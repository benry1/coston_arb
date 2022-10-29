#Actually interact with our arb contract
import settings
from datetime import datetime


ArbitrageContract = settings.RPC.eth.contract(address=settings.ArbitrageAddress, abi=settings.ArbitrageABI)

#TODO: Support triangles around multiple exchanges. Requires contract updates
#TODO: Support more than WNAT cycles
#returns: -1 on revert, 1 on success
def submitArbitrage(path, amountIn, expectedOut) -> int :

    #
    # Get Transaction settings
    #

    #Is Deflationary?
    isDeflationary = False
    for token in settings.deflationaryTokens:
        if (token in path):
            isDeflationary = True
    
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

    if not settings.debug:
        acct = settings.RPC.eth.account.privateKeyToAccount(settings.config["privateKey"])
        tx = ArbitrageContract.functions.executeArb(
                        int(executionAmount * 10**18), 
                        int((executionAmount + 1) * wnat_multiplier), #Require at least 1 token profit
                        path,
                        isDeflationary).build_transaction({
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

    #
    #   Logging
    #

    #TODO: How to get actual profit output from chain ??

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("date and time =", dt_string)
    logMessage = "Found arb opportunity at " + str(dt_string) + ":\n"\
                    + "Optimal: " + str(amountIn) + " Optimal Out: " + str(expectedOut) + "\n"\
                    + "Actual In: " + str(executionAmount) + "\n"\
                    + "Path: " + str(path) + "\n"\
                    + "Includes Deflationary: " + str(isDeflationary) + "\n"\
                    + "Gas Burnt: " + str(gas) + " Status: " + status + "\n\n"
    
    logFile = open("./log/log.txt", "a")
    logFile.write(logMessage)
    logFile.close()

    return 1 if status == "Success" else -1

