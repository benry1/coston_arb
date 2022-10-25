from typing import List
from collections import deque
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
    return retList

def isDuplicatePath(path, seen):
    for prof in seen:
        if path == prof['path']:
            return True
    return False

# Utility function for finding paths in graph
# from source to destination
def findpaths(src: str, pairDB, tokens) -> None:
    maxPathLength = 7
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
    for token in tokens.values():
        neighbors[token] = getNeighbors(token, pairDB)

    
     
    while q:
        # print(path)
        path = q.popleft()
        last = path[len(path) - 1]
 
        # If last vertex is the desired destination
        # then print the path
        if (last == src and len(path) > minPathLength and not isDuplicatePath(path, profitablePaths)):
            # printpath(path)
            Ea, Eb = getEaEb(src, path, pairDB)
            if (Ea < Eb):
                newPath = {'path': path, "Ea": Ea, "Eb": Eb}
                newPath['optimalAmount'] = getOptimalAmount(Ea, Eb)
                if newPath['optimalAmount'] > 0:
                    newPath['outputAmount'] = getAmountOut(newPath['optimalAmount'], Ea, Eb)
                    newPath['profit'] = newPath['outputAmount'] - newPath['optimalAmount']
                    #TODO: Limit by profit margin? Worry about gas fees. etc.
                    profitablePaths.append(newPath)
                    if (len(profitablePaths) > 50 or len(path) > maxPathLength):
                        print(profitablePaths)
                        break
            
 
        # Traverse to all the nodes connected to
        # current vertex and push new path to queue
        for i in range(len(neighbors[last])):
            if (isNotVisited(neighbors[last][i], path)):
                newpath = path.copy()
                newpath.append(neighbors[last][i])
                q.append(newpath)