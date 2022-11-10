"""
Given a path, calculate the virtual pool from SRC->SRC
See README.md for a link to the math.
You can find the "virtual pool size" from A -> C, given A -> B -> C
using some math.
This does that iteratively, over a cycle, until there is Ea, Eb, or
a virtual pool from A -> A

Swap fees are already accounted for.
"""
from decimal import Decimal
import settings


d997 = Decimal(997)
d1000 = Decimal(1000)

def get_amount_out(amount, reserve_in, reserve_out):
    """Given a pool and an amount, how much would be recieved ?"""
    assert amount > 0
    assert reserve_in > 0 and reserve_out > 0
    if not isinstance(amount, Decimal):
        amount = Decimal(amount)
    if not isinstance(reserve_in, Decimal):
        reserve_in = Decimal(reserve_in)
    if not isinstance(reserve_out, Decimal):
        reserve_out = Decimal(reserve_out)
    return d997*amount*reserve_out/(d1000*reserve_in+d997*amount)

def get_optimal_amount(Ea, Eb):
    """Given a virtual A->A pool, how large a trade equalizes pool sizes?"""
    if Ea > Eb:
        return None
    if not isinstance(Ea, Decimal):
        Ea = Decimal(Ea)
    if not isinstance(Eb, Decimal):
        Eb = Decimal(Eb)
    return Decimal(int((Decimal.sqrt(Ea*Eb*d997*d1000)-Ea*d1000)/d997))

def toInt(num):
    """Return Decimal from Int .. ?"""
    return Decimal(int(num))

def get_virtual_pool(token_in, path):
    """Iteratively calcualtes virtual pools until Ea, Eb is decided for A -> A"""
    pairs = get_pairs_in_path(path)

    Ea = None
    Eb = None
    idx = 0
    token_out = token_in
    for pair in pairs:
        if idx == 0:
            if token_in == pair['token0']:
                token_out = pair['token1']
            else:
                token_out = pair['token0']
        if idx == 1:
            Ra = Decimal(pairs[0]['reserve0'])
            Rb = Decimal(pairs[0]['reserve1'])
            if token_in == pairs[0]['token1']:
                Ra, Rb = Rb, Ra
            Rb1 = Decimal(pair['reserve0'])
            Rc = Decimal(pair['reserve1'])
            if token_out == pair['token1']:
                Rb1, Rc = Rc, Rb1
                token_out = pair['token0']
            else:
                token_out = pair['token1']
            Ea = d1000*Ra*Rb1/(d1000*Rb1+d997*Rb)
            Eb = d997*Rb*Rc/(d1000*Rb1+d997*Rb)
        if idx > 1:
            Ra = Ea
            Rb = Eb
            Rb1 = Decimal(pair['reserve0'])
            Rc = Decimal(pair['reserve1'])
            if token_out == pair['token1']:
                Rb1, Rc = Rc, Rb1
                token_out = pair['token0']
            else:
                token_out = pair['token1']
            Ea = d1000*Ra*Rb1/(d1000*Rb1+d997*Rb)
            Eb = d997*Rb*Rc/(d1000*Rb1+d997*Rb)
        idx += 1
    return toInt(Ea), toInt(Eb)



def get_pool(token_0, token_1, exchange):
    """Get the pool sizes from the pair cache"""
    if token_0.lower() < token_1.lower():
        return settings.pair_cache[(exchange, token_0, token_1)]
    return settings.pair_cache[(exchange, token_1, token_0)]

def get_pairs_in_path(path):
    """Get the pool size for every pair in the path"""
    ret_pools = []
    for i in range(len(path) - 1):
        if path[i][1] == path[i + 1][1]:
            continue
        ret_pools.append(get_pool(path[i][1], path[i+1][1], path[i+1][0]))

    return ret_pools
