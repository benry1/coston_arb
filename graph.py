import json
import operator
from typing import List
from collections import deque
from decimal import Decimal
from johnson import simple_cycles
from virtualpools import getAmountOut, getEaEb, getOptimalAmount


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


#Literally shotgun blasts every path possible
#We just stop on all cycles
#so , so , so , so , SO much room for optimization
def findpaths(src: str, pairDB, tokens) -> None:
    maxPathLength = 8
    minPathLength = 3
    profitablePaths = []
    # Create a queue which stores
    # the paths
    q = deque()
 
    # Path vector to store the current path
    path = []
    path.append(src)
    q.append(path.copy())

    #build adjacency list
    neighbors = {}
    nodeValues = {}
    indexValues = {}
    graph = {} # Final adjacency list with number values
    for (idx, token) in enumerate(tokens.values()):
        nodeValues[token] = idx + 1
        indexValues[idx + 1] = token
        neighbors[token] = getNeighbors(token, pairDB)

    for (idx, token) in enumerate(tokens.values()):
        adjacencyList = []
        for neighbor in neighbors[token]:
            adjacencyList.append(nodeValues[neighbor])
        adjacencyList.sort()
        graph[nodeValues[token]] = adjacencyList
    
    # print(nodeValues)
    # print(indexValues)
    # print(graph)

    cycles = simple_cycles(graph)
    cycles = list(cycles)
    cycles.sort(key=len)
    counter = 0
    for cycle in cycles:
        counter = counter + 1
        if counter % 1000 == 0:
            print(counter, len(cycle))
        if len(cycle) < 4:
            continue
        #Reconstruct path
        reconstructed_cycle = []
        cycle.append(1) # The algo leaves off the final step back to start, we need it
        for vertex in cycle:
            reconstructed_cycle.append(indexValues[vertex])
        
        #Get EaEb for reconstructed cycle
        # print(reconstructed_cycle)
        Ea, Eb = getEaEb(src, reconstructed_cycle, pairDB)
        if (Ea < Eb):
            newCycle = {'path': reconstructed_cycle, "Ea": Ea, "Eb": Eb}
            newCycle['optimalAmount'] = getOptimalAmount(Ea, Eb)
            if newCycle['optimalAmount'] > 0:
                newCycle['outputAmount'] = getAmountOut(newCycle['optimalAmount'], Ea, Eb)
                newCycle['profit'] = newCycle['outputAmount'] - newCycle['optimalAmount']
                newCycle['profitRatio'] = newCycle['outputAmount'] / newCycle['optimalAmount']
                #TODO: Limit by profit margin? Worry about gas fees. etc.
                profitablePaths.append(newCycle)

    print("Done searching...")
    # profitablePaths.sort(reverse=True, key=operator.itemgetter('profitRatio'))
    profitablePaths.sort(reverse=True, key=operator.itemgetter('profit'))

    print(profitablePaths[0:10])