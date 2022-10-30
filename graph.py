import operator
import time
from typing import List
from decimal import Decimal

from do_arb import submitArbitrage
from virtualpools import getAmountOut, getEaEb, getOptimalAmount
from settings import wnat_cycles, node_index_values, deflationaryTokens, deflationLevel, pathHistory, statHistory
 
def getNeighbors(asset: str, pairDB):
    fullList = pairDB.getByQuery({"token0": asset}) + pairDB.getByQuery({"token1": asset})
    retList = []
    for pair in fullList:
        if (asset == pair["token0"]):
            retList.append(pair["token1"])
        else:
            retList.append(pair["token0"])
    retList = list(set(retList))
    return retList


#Compile virtual pool size for all known cycles
#Optimizations available here, in "getEaEb"... currently ~0.25s/10000 pools
#Returns: -1 on revert, 0 on no paths found, 1 on success
def findpaths(from_token, sort_key) -> int:

    profitablePaths = []
    profitablePathCounter = 0

    counter = 0
    timer = time.time()
    stepTimer = time.time() #oh no, what are you doing step-timer?
    for cycle in wnat_cycles:
        #Logging
        counter = counter + 1
        if counter % 10000 == 0:
            print("Cycles checked: {ct} Profitable cycles found: {ppc}, Time since last log: {time}".format(ct=counter, ppc=profitablePathCounter, time=time.time() - stepTimer))
            stepTimer = time.time()
        

        #Reconstruct path
        reconstructed_cycle = []
        for vertex in cycle:
            reconstructed_cycle.append(node_index_values[vertex])
        
        #Get EaEb for reconstructed cycle
        Ea, Eb = getEaEb(from_token, reconstructed_cycle)

        #Move on if not profitable
        if (Ea > Eb):
            continue

        newCycle = {'path': reconstructed_cycle, "Ea": Ea, "Eb": Eb}
        newCycle['optimalAmount'] = getOptimalAmount(Ea, Eb)

        #Move on if volume too small
        if newCycle['optimalAmount'] < 1:
            continue

        newCycle['outputAmount'] = getAmountOut(newCycle['optimalAmount'], Ea, Eb)

        #Move on if profit too small
        if newCycle["outputAmount"] < newCycle["optimalAmount"] + Decimal(1):
            continue

        newCycle['profit'] = newCycle['outputAmount'] - newCycle['optimalAmount']
        newCycle['profitRatio'] = newCycle['outputAmount'] / newCycle['optimalAmount']

        #Congrats - you found a reasonably profitable trade!
        #Now .... is it REALLY worth it?
        profitablePaths, profitablePathCounter = vetOpportunity(newCycle, profitablePaths, profitablePathCounter, sort_key)

    print("Done searching, found ", profitablePathCounter, " in ", time.time() - timer)
    print(profitablePaths)

    #Naively execute the best opportunity
    if len(profitablePaths) > 0:
        execute = profitablePaths[0]
        return submitArbitrage(execute["path"], execute["optimalAmount"], execute["outputAmount"])
    else:
        return 0

#Returns: (profitablePathList, #ProfitablePaths, profitablePaths)
def vetOpportunity(newCycle, profitablePathList, profitablePaths, sort_key):
    #Enough profit to offset deflationary tokens?
    path = newCycle["path"]
    requiredProfit = 1.001
    for token in deflationaryTokens:
        if token in path:
            requiredProfit *= deflationLevel[token]

    requiredProfit = Decimal(requiredProfit)

    if newCycle["profitRatio"] < requiredProfit:
        print("Ignoring because {} < {}".format(newCycle['profitRatio'], requiredProfit))
        return profitablePathList, profitablePaths

    #Has this same path failed recently?
    for i in reversed(range(len(pathHistory))):
        if newCycle["path"] == pathHistory[i] and statHistory[i] <= 0:
            print("Ignoring because this path reverted recently.")
            return profitablePathList, profitablePaths

    #Only keep the 10 most profitable trades
    profitablePathList.append(newCycle)
    profitablePathList.sort(reverse=True, key=operator.itemgetter(sort_key))
    profitablePathList = profitablePathList[:10]
    profitablePaths += 1
    return profitablePathList, profitablePaths

