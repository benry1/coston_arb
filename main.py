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

BlazeSwapRouterAddress = "0xEbf80b08f69F359A1713F1C650eEC2F95947Cfe5" # Coston
BlazeSwapContract = settings.RPC.eth.contract(address=BlazeSwapRouterAddress, abi=settings.BlazeSwapRouterABI)

OracleSwapFactoryAddress = "0xDcA8EfcDe7F6Cb36904ea204bb7FCC724889b55d"
OracleSwapContract = settings.RPC.eth.contract(address=OracleSwapFactoryAddress, abi=settings.OracleSwapFactoryABI)

PangolinFactoryAddress = "0xB66E62b25c42D55655a82F8ebf699f2266f329FB"
PangolinFactoryContract = settings.RPC.eth.contract(address=PangolinFactoryAddress, abi=settings.OracleSwapFactoryABI)

# exchanges = ["blazeswap"]
exchanges = ["oracleswap", "pangolin"]
contracts = {
    "pangolin": PangolinFactoryContract,
    "oracleswap": OracleSwapContract,
    "blazeswap": BlazeSwapContract
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
        for exchange in exchanges:
            #Check if DB has this pair
            try1 = pairDB.getByQuery({"symbol0": token0, "symbol1": token1, "exchange": exchange})
            try2 = pairDB.getByQuery({"symbol0": token1, "symbol1": token0, "exchange": exchange})
            if len(try1 + try2) > 0:
                continue

            #Not in DB - Check if is real pair
            try:
                pairAddress = "0x0"
                if exchange == "blazeswap":
                    pairAddress = BlazeSwapContract.functions.pairFor(settings.tokens[token0], settings.tokens[token1]).call()
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
        for exchange in exchanges:
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
                                pair["exchange"] in exchanges and 
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

        if pair["exchange"] not in exchanges:
            continue
        
        #Update pairCache
        settings.pairCache[(pair["exchange"], pair["token0"], pair["token1"])]["reserve0"] = pair["reserve0"] / pow(10, d0)
        settings.pairCache[(pair["exchange"], pair["token0"], pair["token1"])]["reserve1"] = pair["reserve1"] / pow(10, d1)

    print("Update took ", time.time() - start)


#Use modified Johnson algorithm to quickly find all cycles through WNAT
def initializeCycleList():
    #Build adjacency list as Johnson's algorithm needs it
    #Also build an index of node's token value to convert back later
    neighbors = {}
    nodeValues = {}
    graph = {} # Final adjacency list with number values
    nodeValues[("source", settings.tokens["WNAT"])] = 0 #Hard code the start node as a non-exchange-affiliated WNAT
    settings.node_index_values["0"] = ("source", settings.tokens["WNAT"])
    index = 0
    for (token) in settings.tokens.values():
        for exchange in exchanges:
            index += 1
            nodeValues[(exchange, token)] = index
            settings.node_index_values[str(index)] = (exchange, token)
            if token == settings.tokens["WNAT"]:
                neighbors[(exchange, token)] = [("source", token)]
                neighbors[("source", token)] = getNeighbors(token, pairDB)
            else:
                neighbors[(exchange, token)] = getNeighbors(token, pairDB)

    #Give zero element connectivity manually
    sourceAdjacencyList = []
    for (neighborExchange, neighborToken) in neighbors[("source", settings.tokens["WNAT"])]:
        if (neighborToken in settings.tokens.values() and neighborExchange in exchanges):
                sourceAdjacencyList.append(nodeValues[(neighborExchange, neighborToken)])
    graph[0] = sourceAdjacencyList
    #Now handle rest of elements
    for (idx, token) in enumerate(settings.tokens.values()):
        for exchange in exchanges:
            adjacencyList = []
            for (neighborExchange, neighborToken) in neighbors[(exchange, token)]:
                if (neighborToken in settings.tokens.values() and (neighborExchange in exchanges or neighborExchange == "source")):
                    adjacencyList.append(nodeValues[(neighborExchange, neighborToken)])
            adjacencyList.sort()
            graph[nodeValues[(exchange, token)]] = adjacencyList

    # print(graph)
    # print(nodeValues)    
    #With initialized graph,
    #Find all cycles through WNAT.
    timer = time.time()
    cycles_generator = simple_cycles(graph)
    #Limit to length 6 cycles. Question - How low is practical?
    #So far, no difference in opportunities down to <6.
    cycles = filter(lambda cycle: len(cycle) < 10 and len(cycle) > 3, cycles_generator)
    i = 0
    with open("./data/cycles.txt", "w") as file:
        for cycle in cycles:
            i+=1
            if (i % 10000 == 0):
                print(f"Processed {i} cycles...")
            cycle.append(0)
            settings.wnat_cycles.append(cycle)
            
            
            line_str = [str(n) for n in cycle]
            file.write(" ".join(line_str) + "\n")
    
    with open("./data/index_values.json", "w") as file:
        json.dump(settings.node_index_values, file)
    print("Found {} useful cycles in {}".format(len(settings.wnat_cycles), (time.time() - timer)))

def readCycleList():
    timer = time.time()
    with open("./data/cycles.txt", "r") as file:
        line = file.readline()
        count = 0
        while line:
            split = line.split(" ")
            cycle = (int(i) for i in split)
            settings.wnat_cycles.append(list(cycle))
            count += 1
            line = file.readline()
    
    with open("./data/index_values.json", "r") as file:
        data = json.load(file)
        for key in data.keys():
            settings.node_index_values[key] = data[key]
    
    print(settings.node_index_values)
    print("Read {} cycles in {} seconds".format(count, (time.time() - timer)))


# Main Loop
#Returns: -1 on revert, 0 on no opportunities, 1 on success
def tick() -> int:
    updatePairReserves()

    return findpaths(settings.tokens["WNAT"], 'profit')

def initLoop():
    consecutiveReverts = 0
    event_filter = settings.ArbitrageContract.events.Result.createFilter(fromBlock='latest')

    while True:
        status = tick()

        for event in event_filter.get_new_entries():
            handle_event(event)

        if status < 0:
            consecutiveReverts += 1
        else:
            consecutiveReverts = 0
        
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
        initializeCycleList()
    else:
        print("Reading cycle list...")
        readCycleList()
    initializePairCache()    

    initLoop()




main()