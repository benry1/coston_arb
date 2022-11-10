"""
This module handles building the Johnson graph,
and searching all Johnson cycles for arb opportunities
"""
import operator
import time
from decimal import Decimal

from do_arb import submit_arbitrage
from virtualpools import get_amount_out, get_virtual_pool, get_optimal_amount
from settings import source_cycles, node_index_values, deflation_level, path_history, stat_history
import settings



######################
# Building the Graph #
######################

def get_neighbors(asset, pair_db):
    """Get all neighboring tokens, for each token. Return an adjacency list of nodes"""
    full_list = pair_db.getByQuery({"token0": asset}) + pair_db.getByQuery({"token1": asset})
    ret = []
    for pair in full_list:
        if asset == pair["token0"]:
            ret.append((pair["exchange"], pair["token1"]))
        else:
            ret.append((pair["exchange"], pair["token0"]))
    ret = list(set(ret))
    return ret

def get_named_pairs(source):
    """Returns index values for every (exchange, token) pair.
    Modifies node_index_values global in place"""
    node_to_index = {}
    node_to_index[("source", settings.tokens[source])] = 0
    settings.node_index_values[source] = {}
    settings.node_index_values[source]["0"] = ("source", settings.tokens[source])
    index = 0
    for token in settings.tokens.values():
        for exchange in settings.exchanges:
            index += 1
            node_to_index[(exchange, token)] = index
            settings.node_index_values[source][str(index)] = (exchange, token)
    return node_to_index

def get_neighbor_tokens(source, pairDB):
    """Returns an adjacency dictionary, of nodes->nodes, without indexes"""
    neighbors = {}
    for token in settings.tokens.values():
        for exchange in settings.exchanges:
            if token == settings.tokens[source]:
                #Hard code the start node as a non-exchange-affiliated SOURCE
                neighbors[(exchange, token)] = [("source", token)]
                neighbors[("source", token)] = get_neighbors(token, pairDB)
            else:
                neighbors[(exchange, token)] = get_neighbors(token, pairDB)
    return neighbors

def get_johnson_graph(source, neighbors, node_to_index):
    """Retrns an adjacency list, of index->index. For use by the Johnson algorithm"""
    graph = {}

    #Give zero element connectivity manually
    source_adjacent = []
    for (neighbor_exchange, neighbor_token) in neighbors[("source", settings.tokens[source])]:
        if (neighbor_token in settings.tokens.values() and neighbor_exchange in settings.exchanges):
            source_adjacent.append(node_to_index[(neighbor_exchange, neighbor_token)])
    graph[0] = source_adjacent
    #Now handle rest of elements
    for token in settings.tokens.values():
        for exchange in settings.exchanges:
            adjacency_list = []
            for (neighbor_exchange, neighbor_token) in neighbors[(exchange, token)]:
                if (neighbor_token in settings.tokens.values() and
                    (neighbor_exchange in settings.exchanges or neighbor_exchange == "source")):
                    adjacency_list.append(node_to_index[(neighbor_exchange, neighbor_token)])
            adjacency_list.sort()
            graph[node_to_index[(exchange, token)]] = adjacency_list
    return graph


##################################
# Interpret and Search the graph #
##################################

def findpaths(from_symbol, from_token, sort_key) -> int:
    """Compile virtual pool size for all known cycles
    Returns: -1 on revert, 0 on no paths found, 1 on success"""

    profitable_paths = []
    profitable_paths_counter = 0

    counter = 0
    timer = time.time()
    step_timer = time.time() #oh no, what are you doing step-timer?
    for cycle in source_cycles[from_symbol]:
        #Logging
        counter = counter + 1
        if counter % 100000 == 0:
            print(f"Cycles checked: {counter} " +\
                      "Profitable cycles found: {profitable_paths_counter}, " +\
                      "Time since last log: {time.time() - step_timer}")
            step_timer = time.time()

        #Reconstruct path
        #[("source", source), (exchange, token) .... (exchange, source)]
        reconstructed_cycle = []
        for vertex in cycle:
            reconstructed_cycle.append(node_index_values[from_symbol][str(vertex)])

        #Get EaEb for reconstructed cycle
        Ea, Eb = get_virtual_pool(from_token, reconstructed_cycle)

        #Move on if not profitable
        if Ea > Eb:
            continue

        new_cycle = {'path': reconstructed_cycle, "Ea": Ea, "Eb": Eb}
        new_cycle['optimalAmount'] = get_optimal_amount(Ea, Eb)

        #Move on if volume too small
        if new_cycle['optimalAmount'] < 10:
            continue

        new_cycle['outputAmount'] = get_amount_out(new_cycle['optimalAmount'], Ea, Eb)

        #Move on if profit too small
        if new_cycle["outputAmount"] < new_cycle["optimalAmount"] + Decimal(1):
            continue

        new_cycle['profit'] = new_cycle['outputAmount'] - new_cycle['optimalAmount']
        new_cycle['profitRatio'] = new_cycle['outputAmount'] / new_cycle['optimalAmount']

        #Congrats - you found a reasonably profitable trade!
        #Now .... is it REALLY worth it?
        profitable_paths, profitable_paths_counter = vet_opportunity(new_cycle,
                                                                     profitable_paths,
                                                                     profitable_paths_counter,
                                                                     sort_key)

    print(f"Done searching {from_symbol}, " +\
            "found {profitable_paths_counter} in {time.time() - timer}")
    # print(profitable_paths)

    #Naively execute the best opportunity
    if len(profitable_paths) > 0:
        execute = profitable_paths[0]
        return submit_arbitrage(from_symbol,
                                execute["path"],
                                execute["optimalAmount"],
                                execute["outputAmount"])
    return 0

def vet_opportunity(new_cycle, profitable_path_list, profitable_path_counter, sort_key):
    """
    Check if this is a worthwhile try.
    Does it have enough profit to offset deflationary losses?
    Have we failed on this same path recently?
    Returns: (profitable_path_list, #ProfitablePaths, profitable_paths)
    """
    #Enough profit to offset deflationary tokens?
    path = new_cycle["path"]
    required_profit = 1.001
    for (_, token) in path:
        if token in settings.deflationary_tokens:
            required_profit *= deflation_level[token]

    required_profit = Decimal(required_profit)

    if new_cycle["profitRatio"] < required_profit:
        # print("Ignoring because {} < {}".format(new_cycle['profitRatio'], required_profit))
        return profitable_path_list, profitable_path_counter

    #Has this same path failed recently?
    for i in reversed(range(len(path_history))):
        if new_cycle["path"] == path_history[i] and stat_history[i] <= 0:
            print("Ignoring because this path reverted recently.")
            return profitable_path_list, profitable_path_counter

    #Only keep the 10 most profitable trades
    profitable_path_list.append(new_cycle)
    profitable_path_list.sort(reverse=True, key=operator.itemgetter(sort_key))
    profitable_path_list = profitable_path_list[:10]
    profitable_path_counter += 1
    return profitable_path_list, profitable_path_counter
