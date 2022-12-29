"""
This is the main module of the arbitrage bot.
main() method at the bottom will:

1. Get all useful pairs for the exchanges used.
2. Find all valid cycles in the system, based on your settings
3. Begin a loop where each new block, check for arbitrage cycles.
"""
import json
import itertools
import time
from pysondb import db

import settings
from johnson import simple_cycles
from rpc import batch_get_reserves, handle_event
from graph import findpaths, get_named_pairs, get_neighbor_tokens, get_johnson_graph


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

contracts = {
    "pangolin": settings.PangolinFactoryContract,
    "oracleswap": settings.OracleSwapContract,
    "blazeswap": settings.BlazeSwapContract
}

# Save token info if not exist
def bootstrap_token_db():
    """Get and save decimals for each token used"""
    for key, value in settings.tokens.items():
        if len(tokenDB.getByQuery({"symbol": key})) == 0:
            print(key, value)
            token_contract = settings.RPC.eth.contract(address=value, abi=settings.ERC20ABI)
            decimals = token_contract.functions.decimals().call()
            tokenDB.add({"symbol": key, "address": value, "decimals": decimals})

def check_and_save_pair(exchange, token0, token1):
    pair_address = "0x0"
    if exchange == "blazeswap":
        pair_address = contracts[exchange].functions.pairFor(
                                                    settings.tokens[token0],
                                                    settings.tokens[token1]
                                                ).call()
    else:
        pair_address = contracts[exchange].functions.getPair(
                                                    settings.tokens[token0],
                                                    settings.tokens[token1]
                                                ).call()
    pair_contract = settings.RPC.eth.contract(address=pair_address,
                                                abi=settings.BlazeSwapPairABI)
    #Will fail here if invalid
    [r_0, r_1, _] = pair_contract.functions.getReserves().call()

    t_0 = pair_contract.functions.token0().call()
    t_1 = pair_contract.functions.token1().call()
    #Determine if there is enough reserve to be worth it
    token0_info = tokenDB.getByQuery({"address": t_0})[0]
    token1_info = tokenDB.getByQuery({"address": t_1})[0]
    d_0 = token0_info["decimals"]
    d_1 = token1_info["decimals"]
    if (r_0 / 10**d_0 <= settings.min_reserve[token0_info["symbol"]] or
        (r_1 / 10**d_1 <= settings.min_reserve[token1_info["symbol"]])):
        print(exchange, token0, r_0 / 10**d_0,
                token1, r_1 / 10**d_1, " liquidity too low")
        return

    print(f"Adding {token0}/{token1} pair")
    s_0 = token0 if settings.tokens[token0] == t_0 else token1
    s_1 = token1 if s_0 == token0 else token0
    pairDB.add({   "token0": t_0,
                    "symbol0": s_0,
                    "reserve0": r_0 / 10**d_0,
                    "token1": t_1,
                    "symbol1": s_1,
                    "reserve1": r_1 / 10**d_1,
                    "pairAddress": pair_address,
                    "exchange": exchange
            })

def update_pair_db():
    """Update the pair database with any new valid pools"""
    #Get non-repeating pairs
    keys = list(settings.tokens.keys())
    all_pairs = []
    for i, _ in enumerate(keys):
        for j in range(i + 1, len(keys)):
            all_pairs.append((keys[i], keys[j]))

    print(all_pairs)
    for (token0, token1) in all_pairs:
        if token0 == token1:
            continue

        ###create new pair for blaze/pangolin/neo/canaryx/flrfinance/etc
        for exchange in settings.exchanges:
            #Check if DB has this pair
            try1 = pairDB.getByQuery({"symbol0": token0, "symbol1": token1, "exchange": exchange})
            try2 = pairDB.getByQuery({"symbol0": token1, "symbol1": token0, "exchange": exchange})
            if len(try1 + try2) > 0:
                continue

            #Not in DB - Check if is real pair
            try:
                check_and_save_pair(exchange, token0, token1)
            except Exception as exception:
                #TODO: More specific error catching?
                #Invalid pair
                print(exchange, token0, token1, "failed", type(exception), exception)
                continue


def init_pair_cache():
    """Essentially pull the entire PairDB into memory.
    File lookup takes too long for this application."""

    print("Cacheing all pairs")
    #Get all token address pairs
    all_pairs = itertools.product(settings.tokens.values(), repeat=2)

    for (token0, token1) in all_pairs:
        for exchange in settings.exchanges:
            if token0 == token1:
                continue
            #Sort alphabetically
            if token0.lower() > token1.lower():
                token0, token1 = token1, token0

            pair_entry = pairDB.getByQuery({
                "token0": token0,
                "token1": token1,
                "exchange": exchange
            })
            if len(pair_entry) > 0:
                settings.pair_cache[(exchange, token0, token1)] = pair_entry[0]


def update_pair_reserves():
    """For each pair we are using, update the reserves, both in memory and PairCache"""
    all_pair_entries = pairDB.getAll()
    all_pair_entries = list(
                        filter(
                            lambda pair:
                                pair["exchange"] in settings.exchanges and
                                pair["symbol0"] in settings.tokens and
                                pair["symbol1"] in settings.tokens,
                                all_pair_entries)
                            )
    start = time.time()
    #BATCHED
    updated_pairs = batch_get_reserves(all_pair_entries)
    #Normalize to standard decimals
    #TODO: Don't "need" this in memory, might save a few MS by updating cache only
    for pair in updated_pairs:
        d_0 = tokenDB.getByQuery({"symbol": pair["symbol0"]})[0]["decimals"]
        d_1 = tokenDB.getByQuery({"symbol": pair["symbol1"]})[0]["decimals"]
        # pairDB.updateByQuery(
        #         {"pairAddress": pair["pairAddress"]},
        #         {
        #             "reserve0": pair["reserve0"] / pow(10, d_0),
        #             "reserve1": pair["reserve1"]/pow(10, d_1)
        #         }
        #     )

        if pair["exchange"] not in settings.exchanges:
            continue

        #Update pairCache
        settings.pair_cache[(pair["exchange"],
                            pair["token0"],
                            pair["token1"])]["reserve0"] = pair["reserve0"] / pow(10, d_0)
        settings.pair_cache[(pair["exchange"],
                            pair["token0"],
                            pair["token1"])]["reserve1"] = pair["reserve1"] / pow(10, d_1)

    print("Update took ", time.time() - start)

#Use modified Johnson algorithm to quickly find all cycles through the source token
def init_cycle_list(source):
    """Creates a graph of token adjacency.
    Converts to Johnson-compatible graph, and builds a mapping to convert back to token values"""
    node_to_index = get_named_pairs(source)
    neighbors = get_neighbor_tokens(source, pairDB)
    johnson_graph = get_johnson_graph(source, neighbors, node_to_index)

    #With initialized graph,
    #Find all cycles through source.
    timer = time.time()
    cycles_generator = simple_cycles(johnson_graph)
    cycles = filter(lambda cycle: len(cycle) < 8 and len(cycle) > 2, cycles_generator)

    i = 0
    with open(f"./data/cycles_{source}.txt", "w") as file:
        settings.source_cycles[source] = []
        for cycle in cycles:
            i+=1
            if i % 10000 == 0:
                print(f"Processed {i} cycles...")
            cycle.append(0)
            settings.source_cycles[source].append(cycle)


            line_str = [str(n) for n in cycle]
            file.write(" ".join(line_str) + "\n")

    with open(f"./data/index_values_{settings.env}.json", "w") as file:
        json.dump(settings.node_index_values, file)
    print(f"Found {len(settings.source_cycles[source])} useful cycles in {time.time() - timer}")

def read_cycle_list(source):
    """When a cycle list already exists, read from file instead of calculating"""
    timer = time.time()
    with open(f"./data/cycles_{source}.txt", "r") as file:
        settings.source_cycles[source] = []
        line = file.readline()
        count = 0
        while line:
            split = line.split(" ")
            cycle = (int(i) for i in split)
            settings.source_cycles[source].append(list(cycle))
            count += 1
            line = file.readline()

    with open(f"./data/index_values_{settings.env}.json", "r") as file:
        data = json.load(file)
        for source_key in data:
            settings.node_index_values[source_key] = {}
            for token_key in data[source_key]:
                settings.node_index_values[source_key][token_key] = data[source_key][token_key]

    print(f"Read {count} cycles in {time.time() - timer} seconds")



def main_loop():
    """
    Each block that comes in, check all cycles for possible arbitrage.
    Perform the trade if found.
    If there are 5 consecutive reverts, with no brakes, kill the program.
    """
    revert_counter = 0
    event_filter = settings.ArbitrageContract.events.Result.createFilter(fromBlock='latest')
    block_filter = settings.RPC.eth.filter("latest")

    print("Waiting for blocks to begin!")

    while True:
        for block in block_filter.get_new_entries():
            now = time.time()

            update_pair_reserves()
            statuses = []
            for source in settings.source_tokens:
                statuses.append(findpaths(source, settings.tokens[source], 'profit'))


            for event in event_filter.get_new_entries():
                handle_event(event)

            #Should never revert 5 ticks in a row
            #There should at least be a no_paths_found response first!
            if -1 in statuses:
                revert_counter += 1
            else:
                revert_counter = 0

            blocktime = settings.RPC.eth.get_block(block.hex())["timestamp"]
            print(f"Delay was {now - blocktime}\n")

        #Naive negative loop safety
        if revert_counter > 5:
            break


def main():
    """Initialize all settings, pairs, and cycles. Then, kick off the main loop"""
    bootstrap = True
    settings.init_settings()
    print("Hello, Arbitrageur!")
    #Bootstrap with latest tokens and pools
    if bootstrap:
        print("Bootstrapping token DB")
        bootstrap_token_db() #Get token decimals
        print("Updating Pair DB")
        update_pair_db() #Check for any new pairs since last run
        print("Initializing the cycles...")
        for source in settings.source_tokens:
            init_cycle_list(source)
    else:
        print("Reading cycle lists...")
        for source in settings.source_tokens:
            read_cycle_list(source)
    init_pair_cache()

    main_loop()




main()
