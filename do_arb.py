"""
When an arb path is found, actually execute it.
This file also handles logging, both in-file and
to database.
"""
import time

from datetime import datetime
from hexbytes import HexBytes

import settings

def parse_path(in_path, source_symbol):
    """
    Parses the Node path into a path usable by the contract.
    In: [("source", source), (exch1, token), ... ,(exch, source), ("source", source)]
    Out: Paths       : [[source, token1, token2], [token3, token4], [token5, source]]
        Exchanges   : [   exch1,                   exch2,           exch3]
        Deflationary: [    true                      false          false]
    """

    paths = []
    exchanges = []
    deflationary = []

    #Step is (exchange, token)
    prev_token = settings.tokens[source_symbol]
    prev_exch  = "source"
    current_path = []
    for (exchange, token) in in_path:
        if prev_exch not in [exchange, "source"]:
            paths.append(current_path)
            exchanges.append(prev_exch)
            current_path = [prev_token, token]
        else:
            current_path.append(token)

        prev_token = token
        prev_exch = exchange

    #Now check deflationary status for each path
    for path in paths:
        has_deflationary = False
        for token in settings.deflationary_tokens:
            if token in path:
                has_deflationary = True
        deflationary.append(has_deflationary)

    return paths, exchanges, deflationary

def get_execution_amount(amount, source_symbol):
    """Returns viable submission given optimal"""
    if not settings.debug:
        available = settings.ArbitrageContract.functions.getBalance(
                                                settings.tokens[source_symbol]
                                            ).call()
        available = available / settings.eighteen_decimals
        return min(amount, int(available))

    return amount

def send_transaction(execution_amount, paths, exchanges, deflationary, arb_id, multiplier):
    """Handle logic to interact with blockchain"""
    print("Sending tx")
    acct = settings.RPC.eth.account.privateKeyToAccount(settings.config["privateKey"])
    transaction = settings.ArbitrageContract.functions.executeArb(
                    int(execution_amount * settings.eighteen_decimals),
                    paths,
                    exchanges,
                    deflationary,
                    arb_id).build_transaction({
                        'from': acct.address,
                        'nonce': settings.RPC.eth.getTransactionCount(acct.address),
                        'gas': 3000000,
                        'gasPrice': 50000000000 * multiplier
                    })
    signed = acct.signTransaction(transaction)
    tx_hash = settings.RPC.eth.sendRawTransaction(signed.rawTransaction)


    print("Waiting for receipt")
    tx_receipt = settings.RPC.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
    gas = tx_receipt["effectiveGasPrice"] / 10**18 * tx_receipt["gasUsed"]
    status = "Success" if tx_receipt["status"] != 0 else "Revert"
    print(status, gas)

    revert_reason = ""
    if tx_receipt["status"] == 0:
        revert_reason = diagnose_revert(tx_hash)

    return tx_hash, gas, status, revert_reason


def submit_arbitrage(source_symbol, path, amount, expected) -> int :
    """
    Build parameters and submit arbitrage.
    Returns -1 on failure, 1 on success
    """
    #
    # Get Transaction settings
    #

    #Deparse the path
    paths, exchanges, deflationary = parse_path(path, source_symbol)
    print(paths)
    print(exchanges)
    print(deflationary)
    print(amount, expected)

    arb_id = round(time.time() * 1000)

    #Available Balance? Assumes 18 decimals for now..
    execution_amount = get_execution_amount(amount, source_symbol)

    tx_hash = "0xdebug"
    gas = 0
    status = "Debug"
    revert_reason = ""

    #Up the gas if this is a real opportunity
    ideal_profit = (expected - amount) * (execution_amount / amount)
    multiplier = 1
    if ideal_profit > 10:
        multiplier = 5
    if ideal_profit > 100:
        multiplier = 50

    if not settings.debug:
        tx_hash, gas, status, revert_reason = send_transaction(execution_amount,
                                                               paths,
                                                               exchanges,
                                                               deflationary,
                                                               arb_id,
                                                               multiplier)


    ret = 0
    if not settings.debug:
        ret = 1 if status == "Success" else -1

    #
    #   Logging
    #

    settings.path_history.append(path)
    settings.stat_history.append(ret)
    if len(settings.path_history) > 5:
        settings.path_history.pop(0)
        settings.stat_history.pop(0)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    log = "Found " + source_symbol + " arb opportunity at " + str(dt_string)\
                    + " for arb id: " + str(arb_id) + "\n"\
                    + "Optimal: " + str(amount) + " Optimal Out: " + str(expected) + "\n"\
                    + "Actual In: " + str(execution_amount) + "\n"\
                    + "Path: " + str(path) + "\n"\
                    + "Includes Deflationary: " + str(deflationary) + "\n"\
                    + "Gas Burnt: " + str(gas) + " Status: " + status + " " + revert_reason + "\n\n"

    with open("./log/log.txt", "a") as file:
        file.write(log)

    #
    #   MongoDB Logging
    #
    #
    settings.mongo_trades_collection.update_one(
            {
                "tradeId": arb_id
            },
            {
                "$set": {
                    "tradeId": arb_id,
                    "txHash": tx_hash,
                    "source": source_symbol,
                    "path": path,
                    "paths": paths,
                    "exchanges": exchanges,
                    "deflationary": deflationary,
                    "optimalIn": float(amount),
                    "expected": float(expected),
                    "actualIn": float(execution_amount),
                    "gasSpent": float(gas),
                    "status": status,
                    "revert_reason": revert_reason
                }
            },
            upsert=True
        )

    return ret

def diagnose_revert(tx_hash):
    """Call the blockchain to get the revert reason."""
    print("Getting revert reason...")
    transaction = settings.RPC.eth.getTransaction(tx_hash.hex())
    tx_rebuilt = {}

    for key in transaction.keys():
        if isinstance(transaction[key], HexBytes):
            tx_rebuilt[key] = transaction[key].hex()
        else:
            tx_rebuilt[key] = transaction[key]
    tx_rebuilt.pop("gasPrice")

    message = "Uknown"
    try:
        result = settings.RPC.eth.call(tx_rebuilt, tx_rebuilt["blockNumber"] - 1, {})
        print(result)
    except Exception as exception:
        message = str(exception)
    return message
