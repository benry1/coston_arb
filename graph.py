import json
import operator
import time
import random
from typing import List
from collections import deque
from decimal import Decimal
from do_arb import submitArbitrage
from johnson import simple_cycles
from virtualpools import getAmountOut, getEaEb, getOptimalAmount
from settings import wnat_cycles, node_index_values


# Utility function for printing
# the found path in graph
def printpath(path: List[int]) -> None:
     
    size = len(path)
    for i in range(size):
        print(path[i], end = " ")
         
    print()
 
# Utility function to check if current
# vertex is already present in path
def isNotVisited(x: str, path: List[str]) -> int:
 
    size = len(path)
    for i in range(size):
        if (path[i] == x and i != 0):
            return 0
             
    return 1

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

def isDuplicatePath(path, seen):
    for prof in seen:
        if path == prof['path']:
            return True
    return False


#Use Johnson algorithm to quickly find all cycles through WNAT
#Then compute virtual pool size
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
        
        #Only keep the 10 most profitable trades
        profitablePaths.append(newCycle)
        profitablePaths.sort(reverse=True, key=operator.itemgetter(sort_key))
        profitablePaths = profitablePaths[:10]
        profitablePathCounter += 1

    print("Done searching, found ", profitablePathCounter, " in ", time.time() - timer)
    print(profitablePaths)

    #Naively execute the best opportunity
    if len(profitablePaths) > 0:
        execute = profitablePaths[0]
        return submitArbitrage(execute["path"], execute["optimalAmount"], execute["outputAmount"])
    else:
        return 0
