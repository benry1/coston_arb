#Actually interact with our arb contract
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
        print(exchange, token)
        #Time to end the path
        # if token == settings.tokens["WNAT"] and exchange != "source":
        #     print("Base")
        #     currentPath.append(token)
        #     exchanges.append(exchange)
        #     break
        if exchange != lastExch and lastExch != "source":
            print("New exch")
            paths.append(currentPath)
            exchanges.append(lastExch)
            currentPath = [lastToken, token]
        else:
            print("Continue")
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

    
    tx_hash = "0xdebug"
    gas = 0
    status = "Debug"

    #TODO: update this after ABI is updated to support multi-exchange
    if not settings.debug:
        acct = settings.RPC.eth.account.privateKeyToAccount(settings.config["privateKey"])
        tx = ArbitrageContract.functions.executeArb(
                        int(executionAmount * wnat_multiplier), 
                        int((executionAmount + 1) * wnat_multiplier), #Require at least 1 token profit
                        path,
                        False).build_transaction({
                            'from': acct.address,
                            'nonce': settings.RPC.eth.getTransactionCount(acct.address),
                            'gas': 3000000
                        })
        print("signing")
        signed = acct.signTransaction(tx)

        print("sending")
        tx_hash = settings.RPC.eth.sendRawTransaction(signed.rawTransaction)

        print("Waiting for receipt")
        tx_receipt = settings.RPC.eth.wait_for_transaction_receipt(tx_hash)
        print(tx_receipt)
        gas = tx_receipt["effectiveGasPrice"] / 10**18 * tx_receipt["gasUsed"]
        status = "Success" if tx_receipt["status"] != 0 else "Revert"
        print(status, gas)

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

    #TODO: How to get actual profit output from chain ??

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("date and time =", dt_string)
    logMessage = "Found arb opportunity at " + str(dt_string) + ":\n"\
                    + "Optimal: " + str(amountIn) + " Optimal Out: " + str(expectedOut) + "\n"\
                    + "Actual In: " + str(executionAmount) + "\n"\
                    + "Path: " + str(path) + "\n"\
                    + "Includes Deflationary: " + str(False) + "\n"\
                    + "Gas Burnt: " + str(gas) + " Status: " + status + "\n\n"
    
    logFile = open("./log/log.txt", "a")
    logFile.write(logMessage)
    logFile.close()

    return ret

