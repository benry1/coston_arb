from johnson import simple_cycles
from rpc import batchGetReserves
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

# BlazeSwapRouterAddress = "0xEbf80b08f69F359A1713F1C650eEC2F95947Cfe5" # Coston
# BlazeSwapContract = settings.RPC.eth.contract(address=BlazeSwapRouterAddress, abi=settings.BlazeSwapRouterABI)

OracleSwapFactoryAddress = "0xDcA8EfcDe7F6Cb36904ea204bb7FCC724889b55d"
OracleSwapContract = settings.RPC.eth.contract(address=OracleSwapFactoryAddress, abi=settings.OracleSwapFactoryABI)


# PangolinRouterAddress  = "0x6a6C605700f477E56B9542Ca2a3D68B9A7edf599" # Coston
# PangolinRouterAddress = "0x6591cf4E1CfDDEcB4Aa5946c033596635Ba6FB0F"
# PangolinContract  = settings.RPC.eth.contract(address=PangolinRouterAddress, abi=settings.BlazeSwapRouterABI)

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
    allPairs = itertools.product(settings.tokens.keys(), repeat=2)
    for (token0, token1) in allPairs:
        if (token0 == token1):
            continue
        
        #Check if DB has this pair
        try1 = pairDB.getByQuery({"symbol0": token0, "symbol1": token1})
        try2 = pairDB.getByQuery({"symbol0": token1, "symbol1": token0})
        if len(try1 + try2) > 0:
            continue

        #Not in the DB - Check if valid pair
        #by checking reserves.
        ###TODO: Repeat for every exchange, create new pair for blaze/pangolin/neo/canaryx/flrfinance/etc
        try:
            # pairAddress = BlazeSwapContract.functions.pairFor(settings.tokens[token0], settings.tokens[token1]).call()
            pairAddress = OracleSwapContract.functions.getPair(settings.tokens[token0], settings.tokens[token1]).call()
            pairContract = settings.RPC.eth.contract(address=pairAddress, abi=settings.BlazeSwapPairABI)
            [r0, r1, ts] = pairContract.functions.getReserves().call() #Will fail here if invalid
            t0 = pairContract.functions.token0().call()
            t1 = pairContract.functions.token1().call()
            s0 = token0 if settings.tokens[token0] == t0 else token1
            s1 = token1 if s0 == token0 else token0
            pairDB.add({   "token0": t0,
                            "symbol0": s0,
                            "reserve0": r0,
                            "token1": t1,
                            "symbol1": s1,
                            "reserve1": r1,
                            "pairAddress": pairAddress,
                            "exchange": "blazeswap"
                      })
        except Exception as e:
            #Invalid pair
            print(token0, token1, "failed")
            continue


def initializePairCache():
    #Get all token address pairs
    allPairs = itertools.product(settings.tokens.values(), repeat=2)

    for (token0, token1) in allPairs:
        if (token0 == token1):
            continue
        #Sort alphabetically
        if (token0 > token1):
            temp = token1
            token1 = token0
            token0 = temp
        
        pairEntry = pairDB.getByQuery({"token0": token0, "token1": token1})
        if len(pairEntry) > 0:
            settings.pairCache[(token0, token1)] = pairEntry[0]

        
def updatePairReserves():
    allPairObjects = pairDB.getAll()

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
        
        #Update pairCache
        settings.pairCache[(pair["token0"], pair["token1"])]["reserve0"] = pair["reserve0"] / pow(10, d0)
        settings.pairCache[(pair["token0"], pair["token1"])]["reserve1"] = pair["reserve1"] / pow(10, d1)

    print("Update took ", time.time() - start)

def initializeCycleList():
    #Build adjacency list as Johnson's algorithm needs it
    #Also build an index of node's token value to convert back later
    neighbors = {}
    nodeValues = {}
    graph = {} # Final adjacency list with number values
    for (idx, token) in enumerate(settings.tokens.values()):
        nodeValues[token] = idx + 1
        settings.node_index_values[idx + 1] = token
        neighbors[token] = getNeighbors(token, pairDB)

    for (idx, token) in enumerate(settings.tokens.values()):
        adjacencyList = []
        for neighbor in neighbors[token]:
            if (neighbor in settings.tokens.values()):
                adjacencyList.append(nodeValues[neighbor])
        adjacencyList.sort()
        graph[nodeValues[token]] = adjacencyList

    
    #With initialized graph,
    #Find all cycles through WNAT.
    timer = time.time()
    settings.wnat_cycles.extend(simple_cycles(graph))
    print("Found {} useful cycles in {}".format(len(settings.wnat_cycles), (time.time() - timer)))


# Main Loop
#Returns: -1 on revert, 0 on no opportunities, 1 on success
def tick() -> int:
    updatePairReserves()

    return findpaths(settings.tokens["WNAT"], 'profit')

import cProfile
import pstats
# Initialization
def main():
    print("Hello, Arbitrageur!")
    #Bootstrap with latest tokens and pools
    bootstrapTokenDatabase() #Get token decimals
    updatePairDatabase() #Check for any new pairs since last run
    initializePairCache()

    print("Initializing the cycles...")
    initializeCycleList()

    consecutiveReverts = 0
    while True:
        status = tick()
        if status < 0:
            consecutiveReverts += 1
        else:
            consecutiveReverts = 0
        
        #Naive negative loop safety
        if consecutiveReverts > 5:
            break


main()