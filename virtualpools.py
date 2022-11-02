from decimal import Decimal
from settings import pairCache
import itertools
import time


d997 = Decimal(997)
d1000 = Decimal(1000)

def getAmountOut(amountIn, reserveIn, reserveOut):
    assert amountIn > 0
    assert reserveIn > 0 and reserveOut > 0
    if not isinstance(amountIn, Decimal):
        amountIn = Decimal(amountIn)
    if not isinstance(reserveIn, Decimal):
        reserveIn = Decimal(reserveIn)
    if not isinstance(reserveOut, Decimal):
        reserveOut = Decimal(reserveOut)
    return d997*amountIn*reserveOut/(d1000*reserveIn+d997*amountIn)

def getOptimalAmount(Ea, Eb):
    if Ea > Eb:
        return None
    if not isinstance(Ea, Decimal):
        Ea = Decimal(Ea)
    if not isinstance(Eb, Decimal):
        Eb = Decimal(Eb)
    return Decimal(int((Decimal.sqrt(Ea*Eb*d997*d1000)-Ea*d1000)/d997))

def toInt(n):
    return Decimal(int(n))

def getEaEb(tokenIn, path):
    pairs = getPairsInPath(path)

    Ea = None
    Eb = None
    idx = 0
    tokenOut = tokenIn
    for pair in pairs:
        if idx == 0:
            if tokenIn == pair['token0']:
                tokenOut = pair['token1']
            else:
                tokenOut = pair['token0']
        if idx == 1:
            Ra = Decimal(pairs[0]['reserve0'])
            Rb = Decimal(pairs[0]['reserve1'])
            if tokenIn == pairs[0]['token1']:
                temp = Ra
                Ra = Rb
                Rb = temp
            Rb1 = Decimal(pair['reserve0'])
            Rc = Decimal(pair['reserve1'])
            if tokenOut == pair['token1']:
                temp = Rb1
                Rb1 = Rc
                Rc = temp
                tokenOut = pair['token0']
            else:
                tokenOut = pair['token1']
            Ea = d1000*Ra*Rb1/(d1000*Rb1+d997*Rb)
            Eb = d997*Rb*Rc/(d1000*Rb1+d997*Rb)
        if idx > 1:
            Ra = Ea
            Rb = Eb
            Rb1 = Decimal(pair['reserve0'])
            Rc = Decimal(pair['reserve1'])
            if tokenOut == pair['token1']:
                temp = Rb1
                Rb1 = Rc
                Rc = temp
                tokenOut = pair['token0']
            else:
                tokenOut = pair['token1']
            Ea = d1000*Ra*Rb1/(d1000*Rb1+d997*Rb)
            Eb = d997*Rb*Rc/(d1000*Rb1+d997*Rb)
        idx += 1
    return toInt(Ea), toInt(Eb)



def getPool(t0, t1, exchange):
    if (t0.lower() < t1.lower()):
        return pairCache[(exchange, t0, t1)]
    else:
        return pairCache[(exchange, t1, t0)]

def getPairsInPath(path):
    retPools = []
    for i in range(len(path) - 1):
        if (path[i][1] == path[i + 1][1]):
            continue
        retPools.append(getPool(path[i][1], path[i+1][1], path[i+1][0]))
    
    return retPools