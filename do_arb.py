#Actually interact with our arb contract
from decimal import Decimal
from hexbytes import HexBytes
import settings
import time
from datetime import datetime

#In: [("source", source), (exch1, token), (exch2, token), ... ,(exch, source), ("source", source)]
#Out: Paths       : [[source, token1, token2], [token3, token4], [token5, source]]
#     Exchanges   : [   exch1,                   exch2,           exch3]
#     Deflationary: [    true                      false          false]
def parsePath(path, source):
    paths = []
    exchanges = []
    deflationary = []

    #Step is (exchange, token)
    lastToken = settings.tokens[source]
    lastExch  = "source"
    currentPath = []
    for (exchange, token) in path:
        if exchange != lastExch and lastExch != "source":
            paths.append(currentPath)
            exchanges.append(lastExch)
            currentPath = [lastToken, token]
        else:
            currentPath.append(token)

        lastToken = token
        lastExch = exchange

    #Now check deflationary status for each path
    for path in paths:
        hasDeflationary = False
        for token in settings.deflationaryTokens:
            if token in path:
                hasDeflationary = True
        deflationary.append(hasDeflationary)

        
    return paths, exchanges, deflationary

#returns: -1 on revert, 1 on success
def submitArbitrage(source_symbol, path, source, amountIn, expectedOut) -> int :

    #
    # Get Transaction settings
    #

    #Deparse the path
    paths, exchanges, deflationary = parsePath(path)
    print(paths)
    print(exchanges)
    print(deflationary)

    arbId = round(time.time() * 1000)
    
    #Available Balance? Assumes 18 decimals for now..
    executionAmount = amountIn
    if not settings.debug:
        available = settings.ArbitrageContract.functions.getBalance(settings.tokens[source]).call()
        available = available / settings.eighteen_decimals
        executionAmount = min(amountIn, int(available))
    
    tx_hash = "0xdebug"
    gas = 0
    status = "Debug"
    revertReason = ""

    #Up the gas if this is a real opportunity
    idealExecutionProfit = (expectedOut - amountIn) * (executionAmount / amountIn)
    multiplier = 1
    if idealExecutionProfit > 10:
        multiplier = 3
    if idealExecutionProfit > 100:
        multiplier = 5

    if not settings.debug:
        print("Sending tx")
        acct = settings.RPC.eth.account.privateKeyToAccount(settings.config["privateKey"])
        tx = settings.ArbitrageContract.functions.executeArb(
                        int(executionAmount * settings.eighteen_decimals),
                        paths,
                        exchanges,
                        deflationary,
                        arbId).build_transaction({
                            'from': acct.address,
                            'nonce': settings.RPC.eth.getTransactionCount(acct.address),
                            'gas': 3000000,
                            'gasPrice': 50000000000 * multiplier
                        })
        signed = acct.signTransaction(tx)
        tx_hash = settings.RPC.eth.sendRawTransaction(signed.rawTransaction)
        

        print("Waiting for receipt")
        tx_receipt = settings.RPC.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
        gas = tx_receipt["effectiveGasPrice"] / 10**18 * tx_receipt["gasUsed"]
        status = "Success" if tx_receipt["status"] != 0 else "Revert"
        print(status, gas)

        if (tx_receipt["status"] == 0):
            revertReason = diagnoseRevert(tx_hash)
        

    ret = 0
    if not settings.debug:
        ret = 1 if status == "Success" else -1

    #
    #   Logging
    #

    settings.pathHistory.append(path)
    settings.statHistory.append(ret)
    if len(settings.pathHistory) > 5:
        settings.pathHistory.pop(0)
        settings.statHistory.pop(0)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logMessage = "Found " + source_symbol + " arb opportunity at " + str(dt_string) + " for arb id: " + str(arbId) + "\n"\
                    + "Optimal: " + str(amountIn) + " Optimal Out: " + str(expectedOut) + "\n"\
                    + "Actual In: " + str(executionAmount) + "\n"\
                    + "Path: " + str(path) + "\n"\
                    + "Includes Deflationary: " + str(deflationary) + "\n"\
                    + "Gas Burnt: " + str(gas) + " Status: " + status + " " + revertReason + "\n\n"
    
    logFile = open("./log/log.txt", "a")
    logFile.write(logMessage)
    logFile.close()

    #
    #   MongoDB Logging
    #
    #
    settings.tradesCollection.update_one(
            {
                "tradeId": arbId
            },
            { 
                "$set": {
                    "tradeId": arbId,
                    "txHash": tx_hash,
                    "source": source_symbol,
                    "path": path,
                    "paths": paths,
                    "exchanges": exchanges,
                    "deflationary": deflationary,
                    "optimalIn": float(amountIn),
                    "expectedOut": float(expectedOut),
                    "actualIn": float(executionAmount),
                    "gasSpent": float(gas),
                    "status": status,
                    "revertReason": revertReason
                }
            },
            upsert=True
        )

    return ret

def diagnoseRevert(tx_hash):
    print("Getting revert reason...")
    tx = settings.RPC.eth.getTransaction(tx_hash.hex())
    tx_rebuilt = {}

    for key in tx.keys():
        if isinstance(tx[key], HexBytes):
            tx_rebuilt[key] = tx[key].hex()
        else:
            tx_rebuilt[key] = tx[key]
    tx_rebuilt.pop("gasPrice")

    message = "Uknown"
    try:
        result = settings.RPC.eth.call(tx_rebuilt, tx_rebuilt["blockNumber"] - 1, {})
    except Exception as e:
        message = str(e)
    return message
