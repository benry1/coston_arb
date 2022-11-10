"""
Handles all RPC batch calling and parsing
"""
import json
import threading

from web3._utils.request import make_post_request
from web3 import HTTPProvider
from eth_abi import decode_abi
import settings


def handle_event(event):
    """Handle events when emitted from arb contract"""
    event_json = json.loads(settings.RPC.toJSON(event))["args"]
    print("EVENT:", event_json)
    #Upsert the trade with AmountOut and Profit information
    event_json["endBalance"] = event_json["endBalance"] / settings.eighteen_decimals
    event_json["startBalance"]  = event_json["startBalance"] / settings.eighteen_decimals
    event_json["profit"]  = event_json["profit"] / settings.eighteen_decimals
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

def generate_json_rpc(method, params, request_id=1):
    """RPC request boilerplate"""
    return {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': request_id,
    }

def generate_get_reserves_batch(pairs, block_number='latest'):
    """Generate a RPC boilerplate for each getReserves call"""
    contract = settings.RPC.eth.contract(abi=settings.BlazeSwapPairABI)
    for pair in pairs:
        yield generate_json_rpc(
                method='eth_call',
                params=[{
                    'to': pair["pairAddress"],
                    'data': contract.encodeABI(fn_name='getReserves', args=[]),
                    },
                    hex(block_number) if block_number != 'latest' else 'latest',
                    ]
                )

def rpc_response_batch_to_results(response):
    """Decode batch response"""
    for response_item in response:
        yield rpc_response_to_result(response_item)


def rpc_response_to_result(response):
    """Get individual result, or throw error"""
    result = response.get('result')
    if result is None:
        error_message = f"result is None in response {response}."
        raise ValueError(error_message)
    return result

class BatchHTTPProvider(HTTPProvider):
    """Serve batch HTTP requests to provider"""
    def make_batch_request(self, text):
        """Send the already-built batch request"""
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
current_env = settings.config["env"]
batch_provider = BatchHTTPProvider(settings.config[f"rpcUrl_{current_env}"])
def get_reserves(pairs, block_number='latest'):
    """Get reserves for all pairs in batch"""
    r_requests = list(generate_get_reserves_batch(pairs, block_number))
    resp = batch_provider.make_batch_request(json.dumps(r_requests))
    results = list(rpc_response_batch_to_results(resp))
    for i, result in enumerate(results):
        res = decode_abi(['uint256', 'uint256', 'uint256'], bytes.fromhex(result[2:]))
        pairs[i]['reserve0'] = res[0]
        pairs[i]['reserve1'] = res[1]
    return pairs

class MyThread(threading.Thread):
    """Thread class for making several simultaneous batch calls"""
    def __init__(self, func, args):
        super().__init__
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        """Get the result of the request sent on this thread."""
        try:
            return self.result
        except Exception as exception:
            print('thread exception:', exception)
            return None

#Batched reserves
def batch_get_reserves(pairs):
    """Build, Send, Parse a batch of get_reserves calls"""
    if len(pairs) < 200:
        return get_reserves(pairs)

    start = 0
    threads = []
    while start < len(pairs):
        end = start + 200
        if end > len(pairs):
            end = len(pairs)
        thread = MyThread(func=get_reserves, args=(pairs[start:end],))
        thread.start()
        threads.append(thread)
        start = end
    new_pairs = []
    for thread in threads:
        thread.join()
        ret = thread.get_result()
        new_pairs.extend(ret)
    return new_pairs
