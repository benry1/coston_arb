import settings
import json

from web3._utils.request import make_post_request
from web3 import HTTPProvider
from eth_abi import decode_abi


def handle_event(event):
    event_json = json.loads(settings.RPC.toJSON(event))["args"]
    print("EVENT:", event_json)
    #Upsert the trade with AmountOut and Profit information
    event_json["endBalance"] = event_json["endBalance"] / settings.wnat_multiplier
    event_json["startBalance"]  = event_json["startBalance"] / settings.wnat_multiplier
    event_json["profit"]  = event_json["profit"] / settings.wnat_multiplier
    settings.tradesCollection.update_one(
            {
                "tradeId": event_json["id"]
            },
            {
                "$set": {
                    "tradeId": event_json["id"],
                    "profit": (event_json["profit"]),
                    "event": event_json
                }
            },
            upsert=True
        )

def generateJsonRpc(method, params, request_id=1):
    return {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': request_id,
    }

def generateGetReservesBatch(pairs, blockNumber='latest'):
    c = settings.RPC.eth.contract(abi=settings.BlazeSwapPairABI) 
    for pair in pairs:
        yield generateJsonRpc(
                method='eth_call',
                params=[{
                    'to': pair["pairAddress"],
                    'data': c.encodeABI(fn_name='getReserves', args=[]),
                    },
                    hex(blockNumber) if blockNumber != 'latest' else 'latest',
                    ]
                )

def rpc_response_batch_to_results(response):
    for response_item in response:
        yield rpc_response_to_result(response_item)


def rpc_response_to_result(response):
    result = response.get('result')
    if result is None:
        error_message = 'result is None in response {}.'.format(response)
        raise ValueError(error_message)
    return result

class BatchHTTPProvider(HTTPProvider):

    def make_batch_request(self, text):
        self.logger.debug("Making request HTTP. URI: %s, Request: %s",
                          self.endpoint_uri, text)
        request_data = text.encode('utf-8')
        raw_response = make_post_request(
            self.endpoint_uri,
            request_data,
            **self.get_request_kwargs()
        )
        response = self.decode_rpc_response(raw_response)
        self.logger.debug("Getting response HTTP. URI: %s, "
                          "Request: %s, Response: %s",
                          self.endpoint_uri, text, response)
        return response

#Get up to 200 reserves in one call
batch_provider = BatchHTTPProvider(settings.config["rpcUrl"])
def get_reserves(pairs, blockNumber='latest'):
    r = list(generateGetReservesBatch(pairs, blockNumber))
    resp = batch_provider.make_batch_request(json.dumps(r))
    results = list(rpc_response_batch_to_results(resp))
    for i in range(len(results)):
        res = decode_abi(['uint256', 'uint256', 'uint256'], bytes.fromhex(results[i][2:]))
        pairs[i]['reserve0'] = res[0]
        pairs[i]['reserve1'] = res[1]
    return pairs


import threading

class MyThread(threading.Thread):
    def __init__(self, func, args):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception as e:
            print('thread exception:', e)
            return None

#Batched reserves
def batchGetReserves(pairs):
    if len(pairs) < 200:
        return get_reserves(pairs)
    else:
        s = 0
        threads = []
        while s < len(pairs):
            e = s + 200
            if e > len(pairs):
                e = len(pairs)
            t = MyThread(func=get_reserves, args=(pairs[s:e],))
            t.start()
            threads.append(t)
            s = e
        new_pairs = []
        for t in threads:
            t.join()
            ret = t.get_result()
            new_pairs.extend(ret)
        return new_pairs
