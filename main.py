import json
from johnson import simple_cycles
from rpc import batchGetReserves, handle_event
import settings
import itertools
import time

from web3 import Web3
from pysondb import db

from graph import findpaths, getNeighbors


# {
#   "symbol": "testUSD",
#   "token": "0xtestUSDaddress0123456789",
#   "decimals": 6
# }
tokenDB = db.getDb("./data/tokens.json")

# {
#     "token0": "0xtestUSDaddress0123456789",
#     "symbol0": "testUSD",
#     "reserve0": 100000,
#     "token1": "0xtestBTCaddress0987654321",
#     "symbol1": "testBTC",
#     "reserve1": 5,
#     "exchange": "blazeswap",
#     "pairAddress": "0xtestBTCtestUSDPairAddress"
# }
pairDB  = db.getDb("./data/pairs.json")

contracts = {
    "pangolin": settings.PangolinFactoryContract,
    "oracleswap": settings.OracleSwapContract,
    "blazeswap": settings.BlazeSwapContract
}

# Save token info if not exist
def bootstrapTokenDatabase():
    for key in settings.tokens.keys():
        if len(tokenDB.getByQuery({"symbol": key})) == 0:
            print(key, settings.tokens[key])
            tokenAddress = settings.tokens[key]
            tokenContract = settings.RPC.eth.contract(address=tokenAddress, abi=settings.ERC20ABI)
            decimals = tokenContract.functions.decimals().call()
            tokenDB.add({"symbol": key, "address": tokenAddress, "decimals": decimals})

# Update valid pools in the database
# Initialize function - not meant to update reserve values
def updatePairDatabase():
    #Get non-repeating pairs
    k1 = list(settings.tokens.keys())
    k2 = list(settings.tokens.keys())
    allPairs = []
    for i in range(len(k1)):
        for j in range(i + 1, len(k2)):
            allPairs.append((k1[i], k2[j]))
    
    for (token0, token1) in allPairs:
        if (token0 == token1):
            continue
        
        ###create new pair for blaze/pangolin/neo/canaryx/flrfinance/etc
        for exchange in settings.exchanges:
            #Check if DB has this pair
            try1 = pairDB.getByQuery({"symbol0": token0, "symbol1": token1, "exchange": exchange})
            try2 = pairDB.getByQuery({"symbol0": token1, "symbol1": token0, "exchange": exchange})
            if len(try1 + try2) > 0:
                continue

            #Not in DB - Check if is real pair
            try:
                pairAddress = "0x0"
                if exchange == "blazeswap":
                    pairAddress = contracts[exchange].functions.pairFor(settings.tokens[token0], settings.tokens[token1]).call()
                else:
                    pairAddress = contracts[exchange].functions.getPair(settings.tokens[token0], settings.tokens[token1]).call()
                pairContract = settings.RPC.eth.contract(address=pairAddress, abi=settings.BlazeSwapPairABI)
                [r0, r1, ts] = pairContract.functions.getReserves().call() #Will fail here if invalid

                t0 = pairContract.functions.token0().call()
                t1 = pairContract.functions.token1().call()
                #Determine if there is enough reserve to be worth it
                tokenInfo0 = tokenDB.getByQuery({"address": t0})[0]
                tokenInfo1 = tokenDB.getByQuery({"address": t1})[0]
                d0 = tokenInfo0["decimals"]
                d1 = tokenInfo1["decimals"]
                if (r0 / 10**d0 <= settings.minReserve[tokenInfo0["symbol"]]) or (r1 / 10**d1 <= settings.minReserve[tokenInfo1["symbol"]]):
                    print(exchange, token0, r0 / 10**d0, token1, r1 / 10**d1, " liquidity too low")
                    continue

                print(f"Adding {token0}/{token1} pair")
                s0 = token0 if settings.tokens[token0] == t0 else token1
                s1 = token1 if s0 == token0 else token0
                pairDB.add({   "token0": t0,
                                "symbol0": s0,
                                "reserve0": r0 / 10**d0,
                                "token1": t1,
                                "symbol1": s1,
                                "reserve1": r1 / 10**d1,
                                "pairAddress": pairAddress,
                                "exchange": exchange
                        })
            except Exception as e:
                #Invalid pair
                print(exchange, token0, token1, "failed", type(e))
                continue


def initializePairCache():
    print("Cacheing all pairs")
    #Get all token address pairs
    allPairs = itertools.product(settings.tokens.values(), repeat=2)

    
    for (token0, token1) in allPairs:
        for exchange in settings.exchanges:
            if (token0 == token1):
                continue
            #Sort alphabetically
            if (token0.lower() > token1.lower()):
                temp = token1
                token1 = token0
                token0 = temp

            pairEntry = pairDB.getByQuery({"token0": token0, "token1": token1, "exchange": exchange})
            if len(pairEntry) > 0:
                settings.pairCache[(exchange, token0, token1)] = pairEntry[0]

        
def updatePairReserves():
    allPairObjects = pairDB.getAll()
    allPairObjects = list(
                        filter(
                            lambda pair: 
                                pair["exchange"] in settings.exchanges and 
                                pair["symbol0"] in settings.tokens.keys() and
                                pair["symbol1"] in settings.tokens.keys(), allPairObjects))
    start = time.time()
    #BATCHED
    updatedPairs = batchGetReserves(allPairObjects)
    #Normalize to standard decimals
    for pair in updatedPairs:
        d0 = tokenDB.getByQuery({"symbol": pair["symbol0"]})[0]["decimals"]
        d1 = tokenDB.getByQuery({"symbol": pair["symbol1"]})[0]["decimals"]
        pairDB.updateByQuery(
                {"pairAddress": pair["pairAddress"]}, 
                {"reserve0": pair["reserve0"] / pow(10, d0), "reserve1": pair["reserve1"]/pow(10, d1) }
            )

        if pair["exchange"] not in settings.exchanges:
            continue
        
        #Update pairCache
        settings.pairCache[(pair["exchange"], pair["token0"], pair["token1"])]["reserve0"] = pair["reserve0"] / pow(10, d0)
        settings.pairCache[(pair["exchange"], pair["token0"], pair["token1"])]["reserve1"] = pair["reserve1"] / pow(10, d1)

    print("Update took ", time.time() - start)


#Use modified Johnson algorithm to quickly find all cycles through the source token
def initializeCycleList(source):
    #Build adjacency list as Johnson's algorithm needs it
    #Also build an index of node's token value to convert back later
    neighbors = {}
    nodeValues = {}
    graph = {} # Final adjacency list with number values
    nodeValues[("source", settings.tokens[source])] = 0 #Hard code the start node as a non-exchange-affiliated SOURCE
    settings.node_index_values[source] = {}
    settings.node_index_values[source]["0"] = ("source", settings.tokens[source])
    index = 0
    for (token) in settings.tokens.values():
        for exchange in settings.exchanges:
            index += 1
            nodeValues[(exchange, token)] = index
            settings.node_index_values[source][str(index)] = (exchange, token)
            if token == settings.tokens[source]:
                neighbors[(exchange, token)] = [("source", token)]
                neighbors[("source", token)] = getNeighbors(token, pairDB)
            else:
                neighbors[(exchange, token)] = getNeighbors(token, pairDB)

    #Give zero element connectivity manually
    sourceAdjacencyList = []
    for (neighborExchange, neighborToken) in neighbors[("source", settings.tokens[source])]:
        if (neighborToken in settings.tokens.values() and neighborExchange in settings.exchanges):
                sourceAdjacencyList.append(nodeValues[(neighborExchange, neighborToken)])
    graph[0] = sourceAdjacencyList
    #Now handle rest of elements
    for (idx, token) in enumerate(settings.tokens.values()):
        for exchange in settings.exchanges:
            adjacencyList = []
            for (neighborExchange, neighborToken) in neighbors[(exchange, token)]:
                if (neighborToken in settings.tokens.values() and (neighborExchange in settings.exchanges or neighborExchange == "source")):
                    adjacencyList.append(nodeValues[(neighborExchange, neighborToken)])
            adjacencyList.sort()
            graph[nodeValues[(exchange, token)]] = adjacencyList

    # print(graph)
    # print(nodeValues)    
    #With initialized graph,
    #Find all cycles through source.
    timer = time.time()
    cycles_generator = simple_cycles(graph)
    #Limit to length 6 cycles. Question - How low is practical?
    #So far, no difference in opportunities down to <6.
    cycles = filter(lambda cycle: len(cycle) < 10 and len(cycle) > 2, cycles_generator)
    i = 0
    with open(f"./data/cycles_{source}.txt", "w") as file:
        settings.source_cycles[source] = []
        for cycle in cycles:
            i+=1
            if (i % 10000 == 0):
                print(f"Processed {i} cycles...")
            cycle.append(0)
            settings.source_cycles[source].append(cycle)
            
            
            line_str = [str(n) for n in cycle]
            file.write(" ".join(line_str) + "\n")
    
    with open(f"./data/index_values.json", "w") as file:
        json.dump(settings.node_index_values, file)
    print("Found {} useful cycles in {}".format(len(settings.source_cycles[source]), (time.time() - timer)))

def readCycleList(source):
    timer = time.time()
    with open(f"./data/cycles_{source}.txt", "r") as file:
        settings.source_cycles[source] = []
        line = file.readline()
        count = 0
        while line:
            split = line.split(" ")
            cycle = (int(i) for i in split)
            settings.source_cycles[source].append(list(cycle))
            count += 1
            line = file.readline()
    
    with open(f"./data/index_values.json", "r") as file:
        data = json.load(file)
        for source_key in data.keys():
            settings.node_index_values[source_key] = {}
            for token_key in data[source_key].keys():
                settings.node_index_values[source_key][token_key] = data[source_key][token_key]
    
    print("Read {} cycles in {} seconds".format(count, (time.time() - timer)))

    

def initLoop():
    consecutiveReverts = 0
    event_filter = settings.ArbitrageContract.events.Result.createFilter(fromBlock='latest')
    block_filter = settings.RPC.eth.filter("latest")

    print("Waiting for blocks to begin!")

    while True:
        for block in block_filter.get_new_entries():
            now = time.time()
            
            updatePairReserves()
            statuses = []
            for source in settings.source_tokens:
                statuses.append(findpaths(source, settings.tokens[source], 'profit'))


            for event in event_filter.get_new_entries():
                handle_event(event)

            #Should never revert 5 ticks in a row
            #There should at least be a no_paths_found response first!
            if -1 in statuses:
                consecutiveReverts += 1
            else:
                consecutiveReverts = 0

            blocktime = settings.RPC.eth.get_block(block.hex())["timestamp"]
            print("Delay was {}\n".format(now - blocktime))
            
        #Naive negative loop safety
        if consecutiveReverts > 5:
            break

# Initialization
def main():
    bootstrap = False
    print("Hello, Arbitrageur!")
    #Bootstrap with latest tokens and pools
    if bootstrap:
        print("Bootstrapping token DB")
        bootstrapTokenDatabase() #Get token decimals
        print("Updating Pair DB")
        updatePairDatabase() #Check for any new pairs since last run
        print("Initializing the cycles...")
        for source in settings.source_tokens:
            initializeCycleList(source)
    else:
        print("Reading cycle lists...")
        for source in settings.source_tokens:
            readCycleList(source)
    initializePairCache()  

    # print(settings.source_cycles.keys(), len(settings.source_cycles["WNAT"]))  
    # print(settings.node_index_values)

    initLoop()




main()