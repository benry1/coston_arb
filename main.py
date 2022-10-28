from rpc import batchGetReserves
import settings
import itertools
import time

from web3 import Web3
from pysondb import db

from graph import findpaths


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

BlazeSwapRouterAddress = "0xEbf80b08f69F359A1713F1C650eEC2F95947Cfe5"
BlazeSwapContract = settings.RPC.eth.contract(address=BlazeSwapRouterAddress, abi=settings.BlazeSwapRouterABI)


PangolinRouterAddress  = "0x6a6C605700f477E56B9542Ca2a3D68B9A7edf599"
PangolinContract  = settings.RPC.eth.contract(address=PangolinRouterAddress, abi=settings.BlazeSwapRouterABI)

# Save token info if not exist
def bootstrapTokenDatabase():
    for key in settings.tokens.keys():
        if len(tokenDB.getByQuery({"symbol": key})) == 0:
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
        if len(try1) > 0 or len(try2) > 0:
            continue

        #Not in the DB - Check if valid pair
        #by checking reserves.
        ###TODO: Repeat for every exchange, create new pair for blaze/pangolin/neo/etc
        try:
            pairAddress = BlazeSwapContract.functions.pairFor(settings.tokens[token0], settings.tokens[token1]).call()
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

    print("Update took ", time.time() - start)

# Main Loop
#Returns: -1 on revert, 0 on no opportunities, 1 on success
def tick() -> int:
    updatePairReserves()

    return findpaths(settings.tokens["WCFLR"], pairDB, settings.tokens, 'profit')

# Initialization
def main():

    #Bootstrap with latest tokens and pools
    bootstrapTokenDatabase() #Get token decimals
    # updatePairDatabase() #Check for any new pairs since last run

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