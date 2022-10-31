#Actually interact with our arb contract
from hexbytes import HexBytes
import settings
from datetime import datetime


ArbitrageContract = settings.RPC.eth.contract(address=settings.ArbitrageAddress, abi=settings.ArbitrageABI)

#In: [("source", wnat), (exch1, token), (exch2, token), ... ,(exch, wnat), ("source", wnat)]
#Out: Paths       : [[wnat, token1, token2], [token3, token4], [token5, wnat]]
#     Exchanges   : [   exch1,                   exch2,           exch3]
#     Deflationary: [    true                      false          false]
#TODO: Implement
def parsePath(path):
    paths = []
    exchanges = []
    deflationary = []

    #Step is (exchange, token)
    lastToken = settings.tokens["WNAT"]
    lastExch  = "source"
    currentPath = []
    for (exchange, token) in path:
        #Time to end the path
        # if token == settings.tokens["WNAT"] and exchange != "source":
        #     print("Base")
        #     currentPath.append(token)
        #     exchanges.append(exchange)
        #     break
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
            if token in path and path[-1] != token:
                hasDeflationary = True
        deflationary.append(hasDeflationary)

        
    return paths, exchanges, deflationary

#TODO: Support more than WNAT cycles
#returns: -1 on revert, 1 on success
def submitArbitrage(path, amountIn, expectedOut) -> int :

    #
    # Get Transaction settings
    #

    #Deparse the path
    paths, exchanges, deflationary = parsePath(path)
    print(path)
    print(paths)
    print(exchanges)
    print(deflationary)
    
    #Available Balance? Assumes WNAT for now..
    executionAmount = amountIn
    wnat_multiplier = 10 ** 18
    if not settings.debug:
        available = ArbitrageContract.functions.getBalance(settings.tokens["WNAT"]).call()
        available = available / wnat_multiplier
        executionAmount = min(amountIn, int(available))

    requiredOutput = (executionAmount + 1) #Require at least 1 token profit
    
    tx_hash = "0xdebug"
    gas = 0
    status = "Debug"

    #TODO: update this after ABI is updated to support multi-exchange
    if not settings.debug:
        print("Sending tx")
        acct = settings.RPC.eth.account.privateKeyToAccount(settings.config["privateKey"])
        tx = ArbitrageContract.functions.executeArb(
                        int(executionAmount * wnat_multiplier), 
                        int(requiredOutput * wnat_multiplier), 
                        paths,
                        exchanges,
                        deflationary).build_transaction({
                            'from': acct.address,
                            'nonce': settings.RPC.eth.getTransactionCount(acct.address),
                            'gas': 3000000
                        })
        signed = acct.signTransaction(tx)
        tx_hash = settings.RPC.eth.sendRawTransaction(signed.rawTransaction)
        

        print("Waiting for receipt")
        tx_receipt = settings.RPC.eth.wait_for_transaction_receipt(tx_hash)
        gas = tx_receipt["effectiveGasPrice"] / 10**18 * tx_receipt["gasUsed"]
        status = "Success" if tx_receipt["status"] != 0 else "Revert:"
        print(status, gas)

        if (tx_receipt["status"] == 0):
            status = status + " " + diagnoseRevert(tx_hash)

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
    logMessage = "Found arb opportunity at " + str(dt_string) + ":\n"\
                    + "Optimal: " + str(amountIn) + " Optimal Out: " + str(expectedOut) + "\n"\
                    + "Actual In: " + str(executionAmount) + " Min Out: " + str(requiredOutput) + "\n"\
                    + "Path: " + str(path) + "\n"\
                    + "Includes Deflationary: " + str(False) + "\n"\
                    + "Gas Burnt: " + str(gas) + " Status: " + status + "\n\n"
    
    logFile = open("./log/log.txt", "a")
    logFile.write(logMessage)
    logFile.close()

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
