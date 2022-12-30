# Define Globals

from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import dotenv_values
import pymongo


config = dotenv_values(".env")

debug = config["debug"] == "True"
env   = config["env"]


#
#
#       Contract and RPC
#
#

RPC = Web3(Web3.HTTPProvider(config[f"rpcUrl_{env}"]))
RPC.middleware_onion.inject(geth_poa_middleware, layer=0)

ERC20ABI = '''[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"payable":true,"stateMutability":"payable","type":"fallback"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]'''
BlazeSwapRouterABI = '''[{"type":"constructor","stateMutability":"nonpayable","inputs":[{"type":"address","name":"_factory","internalType":"address"},{"type":"address","name":"_wNat","internalType":"address"},{"type":"bool","name":"_splitFee","internalType":"bool"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256","name":"amountA","internalType":"uint256"},{"type":"uint256","name":"amountB","internalType":"uint256"},{"type":"uint256","name":"liquidity","internalType":"uint256"}],"name":"addLiquidity","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"},{"type":"uint256","name":"amountADesired","internalType":"uint256"},{"type":"uint256","name":"amountBDesired","internalType":"uint256"},{"type":"uint256","name":"amountAMin","internalType":"uint256"},{"type":"uint256","name":"amountBMin","internalType":"uint256"},{"type":"uint256","name":"feeBipsA","internalType":"uint256"},{"type":"uint256","name":"feeBipsB","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"payable","outputs":[{"type":"uint256","name":"amountToken","internalType":"uint256"},{"type":"uint256","name":"amountNAT","internalType":"uint256"},{"type":"uint256","name":"liquidity","internalType":"uint256"}],"name":"addLiquidityNAT","inputs":[{"type":"address","name":"token","internalType":"address"},{"type":"uint256","name":"amountTokenDesired","internalType":"uint256"},{"type":"uint256","name":"amountTokenMin","internalType":"uint256"},{"type":"uint256","name":"amountNATMin","internalType":"uint256"},{"type":"uint256","name":"feeBipsToken","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"factory","inputs":[]},{"type":"function","stateMutability":"pure","outputs":[{"type":"uint256","name":"amountIn","internalType":"uint256"}],"name":"getAmountIn","inputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"},{"type":"uint256","name":"reserveIn","internalType":"uint256"},{"type":"uint256","name":"reserveOut","internalType":"uint256"}]},{"type":"function","stateMutability":"pure","outputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"}],"name":"getAmountOut","inputs":[{"type":"uint256","name":"amountIn","internalType":"uint256"},{"type":"uint256","name":"reserveIn","internalType":"uint256"},{"type":"uint256","name":"reserveOut","internalType":"uint256"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"uint256[]","name":"amounts","internalType":"uint256[]"}],"name":"getAmountsIn","inputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"uint256[]","name":"amounts","internalType":"uint256[]"}],"name":"getAmountsOut","inputs":[{"type":"uint256","name":"amountIn","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"uint256","name":"","internalType":"uint256"},{"type":"uint256","name":"","internalType":"uint256"}],"name":"getReserves","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"bytes[]","name":"results","internalType":"bytes[]"}],"name":"multicall","inputs":[{"type":"bytes[]","name":"data","internalType":"bytes[]"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"pairFor","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"}]},{"type":"function","stateMutability":"pure","outputs":[{"type":"uint256","name":"amountB","internalType":"uint256"}],"name":"quote","inputs":[{"type":"uint256","name":"amountA","internalType":"uint256"},{"type":"uint256","name":"reserveA","internalType":"uint256"},{"type":"uint256","name":"reserveB","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256","name":"amountA","internalType":"uint256"},{"type":"uint256","name":"amountB","internalType":"uint256"}],"name":"removeLiquidity","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"},{"type":"uint256","name":"liquidity","internalType":"uint256"},{"type":"uint256","name":"amountAMin","internalType":"uint256"},{"type":"uint256","name":"amountBMin","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256","name":"amountToken","internalType":"uint256"},{"type":"uint256","name":"amountNAT","internalType":"uint256"}],"name":"removeLiquidityNAT","inputs":[{"type":"address","name":"token","internalType":"address"},{"type":"uint256","name":"liquidity","internalType":"uint256"},{"type":"uint256","name":"amountTokenMin","internalType":"uint256"},{"type":"uint256","name":"amountNATMin","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256","name":"amountToken","internalType":"uint256"},{"type":"uint256","name":"amountNAT","internalType":"uint256"}],"name":"removeLiquidityNATWithPermit","inputs":[{"type":"address","name":"token","internalType":"address"},{"type":"uint256","name":"liquidity","internalType":"uint256"},{"type":"uint256","name":"amountTokenMin","internalType":"uint256"},{"type":"uint256","name":"amountNATMin","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"},{"type":"bool","name":"approveMax","internalType":"bool"},{"type":"uint8","name":"v","internalType":"uint8"},{"type":"bytes32","name":"r","internalType":"bytes32"},{"type":"bytes32","name":"s","internalType":"bytes32"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256","name":"amountA","internalType":"uint256"},{"type":"uint256","name":"amountB","internalType":"uint256"}],"name":"removeLiquidityWithPermit","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"},{"type":"uint256","name":"liquidity","internalType":"uint256"},{"type":"uint256","name":"amountAMin","internalType":"uint256"},{"type":"uint256","name":"amountBMin","internalType":"uint256"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"},{"type":"bool","name":"approveMax","internalType":"bool"},{"type":"uint8","name":"v","internalType":"uint8"},{"type":"bytes32","name":"r","internalType":"bytes32"},{"type":"bytes32","name":"s","internalType":"bytes32"}]},{"type":"function","stateMutability":"nonpayable","outputs":[],"name":"selfPermit","inputs":[{"type":"address","name":"token","internalType":"address"},{"type":"uint256","name":"value","internalType":"uint256"},{"type":"uint256","name":"deadline","internalType":"uint256"},{"type":"uint8","name":"v","internalType":"uint8"},{"type":"bytes32","name":"r","internalType":"bytes32"},{"type":"bytes32","name":"s","internalType":"bytes32"}]},{"type":"function","stateMutability":"payable","outputs":[{"type":"uint256[]","name":"amountsSent","internalType":"uint256[]"},{"type":"uint256[]","name":"amountsRecv","internalType":"uint256[]"}],"name":"swapExactNATForTokens","inputs":[{"type":"uint256","name":"amountOutMin","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256[]","name":"amountsSent","internalType":"uint256[]"},{"type":"uint256[]","name":"amountsRecv","internalType":"uint256[]"}],"name":"swapExactTokensForNAT","inputs":[{"type":"uint256","name":"amountIn","internalType":"uint256"},{"type":"uint256","name":"amountOutMin","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256[]","name":"amountsSent","internalType":"uint256[]"},{"type":"uint256[]","name":"amountsRecv","internalType":"uint256[]"}],"name":"swapExactTokensForTokens","inputs":[{"type":"uint256","name":"amountIn","internalType":"uint256"},{"type":"uint256","name":"amountOutMin","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"payable","outputs":[{"type":"uint256[]","name":"amounts","internalType":"uint256[]"}],"name":"swapNATForExactTokens","inputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256[]","name":"amounts","internalType":"uint256[]"}],"name":"swapTokensForExactNAT","inputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"},{"type":"uint256","name":"amountInMax","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"uint256[]","name":"amounts","internalType":"uint256[]"}],"name":"swapTokensForExactTokens","inputs":[{"type":"uint256","name":"amountOut","internalType":"uint256"},{"type":"uint256","name":"amountInMax","internalType":"uint256"},{"type":"address[]","name":"path","internalType":"address[]"},{"type":"address","name":"to","internalType":"address"},{"type":"uint256","name":"deadline","internalType":"uint256"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"wNat","inputs":[]},{"type":"receive","stateMutability":"payable"}]'''
BlazeSwapPairABI = '''[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Burn","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"Mint","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount0Out","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1Out","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Swap","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint112","name":"reserve0","type":"uint112"},{"indexed":false,"internalType":"uint112","name":"reserve1","type":"uint112"}],"name":"Sync","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"MINIMUM_LIQUIDITY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"PERMIT_TYPEHASH","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"burn","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_token0","type":"address"},{"internalType":"address","name":"_token1","type":"address"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"kLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"mint","outputs":[{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"price0CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"price1CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"skim","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount0Out","type":"uint256"},{"internalType":"uint256","name":"amount1Out","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"swap","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"sync","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]'''
OracleSwapFactoryABI = '''[{"type":"constructor","stateMutability":"nonpayable","inputs":[{"type":"address","name":"_feeToSetter","internalType":"address"}]},{"type":"event","name":"PairCreated","inputs":[{"type":"address","name":"token0","internalType":"address","indexed":true},{"type":"address","name":"token1","internalType":"address","indexed":true},{"type":"address","name":"pair","internalType":"address","indexed":false},{"type":"uint256","name":"","internalType":"uint256","indexed":false}],"anonymous":false},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"allPairs","inputs":[{"type":"uint256","name":"","internalType":"uint256"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"uint256","name":"","internalType":"uint256"}],"name":"allPairsLength","inputs":[]},{"type":"function","stateMutability":"nonpayable","outputs":[{"type":"address","name":"pair","internalType":"address"}],"name":"createPair","inputs":[{"type":"address","name":"tokenA","internalType":"address"},{"type":"address","name":"tokenB","internalType":"address"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"feeTo","inputs":[]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"feeToSetter","inputs":[]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"getPair","inputs":[{"type":"address","name":"","internalType":"address"},{"type":"address","name":"","internalType":"address"}]},{"type":"function","stateMutability":"view","outputs":[{"type":"address","name":"","internalType":"address"}],"name":"migrator","inputs":[]},{"type":"function","stateMutability":"pure","outputs":[{"type":"bytes32","name":"","internalType":"bytes32"}],"name":"pairCodeHash","inputs":[]},{"type":"function","stateMutability":"nonpayable","outputs":[],"name":"setFeeTo","inputs":[{"type":"address","name":"_feeTo","internalType":"address"}]},{"type":"function","stateMutability":"nonpayable","outputs":[],"name":"setFeeToSetter","inputs":[{"type":"address","name":"_feeToSetter","internalType":"address"}]},{"type":"function","stateMutability":"nonpayable","outputs":[],"name":"setMigrator","inputs":[{"type":"address","name":"_migrator","internalType":"address"}]}]'''
ArbitrageABI = config["arbABI"]
ArbitrageAddress = config[f"arbAddress_{env}"]
ArbitrageContract = RPC.eth.contract(address=ArbitrageAddress, abi=ArbitrageABI)


#
#   Tokens Config
#
#



#Just don't want to do file access every time
eighteen_decimals = 10**18

tokens = {}
min_reserve = {}
source_tokens = []
deflationary_tokens = []

#What is the minimum profit margin
#To accept a cycle using this deflationary token?
deflation_level = {
    "0x8d32E20d119d936998575B4AAff66B9999011D27": 1.101,
    "0xf810576A68C3731875BDe07404BE815b16fC0B4e": 1.01,
    "0xF3D185162E55463264B0d63DD4497093B00F57d1": 1.01
}


####################
# Exchanges Config #
####################

# BlazeSwapRouterAddress = "0xf0D01450C037DB2903CF5Ff638Dd1e2e6B0EEDF4" # Coston
BlazeSwapRouterAddress = "0xAfcED6d85416bC3a3158563B087DB305F40FbaF3" #Songbird
BlazeSwapContract = RPC.eth.contract(address=BlazeSwapRouterAddress, abi=BlazeSwapRouterABI)

OracleSwapFactoryAddress = "0xDcA8EfcDe7F6Cb36904ea204bb7FCC724889b55d"
OracleSwapContract = RPC.eth.contract(address=OracleSwapFactoryAddress, abi=OracleSwapFactoryABI)

PangolinFactoryAddress = "0xB66E62b25c42D55655a82F8ebf699f2266f329FB"
PangolinFactoryContract = RPC.eth.contract(address=PangolinFactoryAddress, abi=OracleSwapFactoryABI)

exchanges = []

#
#       Graph Helpers Initialized once
#
#
pair_cache = {}
source_cycles = {}
node_index_values = {}


#
#
#   Arb Path History
#
#

# = [ [path1], [path2], .... , [mostRecentPath] ]
path_history = []

# = [ -1, 1, 0, 0, 1, -1, -1]
stat_history = []

#
#   MongoDB
#
#

mongoURI = config["mongoURI"]
mongoDBName = config["mongoDBName"]
mongo = pymongo.MongoClient(mongoURI)
arb_db = mongo[mongoDBName]
mongo_trades_collection = arb_db["trades"]


#Build the environment based on which network we're on
def init_settings():
    global tokens, min_reserve, exchanges, deflationary_tokens, source_tokens
    if env == "coston":
        tokens = {
            "WCFLR":   "0x767b25A658E8FC8ab6eBbd52043495dB61b4ea91",
            "testBTC": "0x2A9EAE71Bf8d7392b2c9409a8F036fcf6F88fc44",
            "testXRP": "0x73cADB6ce663983dA2507e160543d84D8bA29EfA",
            "testADA": "0x8048C36831d8F7e40365Cf11cff6Db66293ec9e9",
            "testDOGE":"0xFf00529cE94b6256bDF4eeD7774d4301f0Ec6557",
            "testETH": "0x3B1576169dBA342c289957D83aC43a394137115b",
            "testLTC": "0x73B6db4b0Aed010487CFD1138fF8d7c908151181",
            "testEUR": "0xdA501af976Af8DBF24A1545803f04F508f1BF2aE",
            "testUSD": "0x0B79FC311A7b89ed328b7AbA6f18495996eBb339",
            "testXAU": "0xF3D185162E55463264B0d63DD4497093B00F57d1",
        }
        min_reserve = {
            "WCFLR":   0,
            "testBTC": 0,
            "testXRP": 0,
            "testADA": 0,
            "testDOGE":0,
            "testETH": 0,
            "testLTC": 0,
            "testEUR": 0,
            "testUSD": 0,
            "testXAU": 0,
        }
        deflationary_tokens = ["0xF3D185162E55463264B0d63DD4497093B00F57d1"] # Coston
        exchanges = ["blazeswap"]
        source_tokens = ["WCFLR"]
    elif env == "songbird":
        tokens = {
            "WSGB": "0x02f0826ef6aD107Cfc861152B32B52fD11BaB9ED",
            "SFORT": "0x9E2E6c16803878C18E54Ed74F05AeafCCe464626",
            "DOOD": "0x612c20D14493dC6a389603aEF56006AD6a09A76f",
            "sDOOD": "0x697bb3B5E1eCf4fEbE6016321b0648d3d6C270B6",
            "ORACLE": "0xD7565b16b65376e2Ddb6c71E7971c7185A7Ff3Ff",
            "xORACLE": "0x5795377c85e0fdF6370fae1B74Fe03b930C4a892",
            "PRO": "0xf810576A68C3731875BDe07404BE815b16fC0B4e", #Deflationary (1%)
            "HS": "0x9dC8639bff70B019088f0b7D960561654269B5BE",
            "EXFI": "0xC348F894d0E939FE72c467156E6d7DcbD6f16e21",
            "SFIN": "0x0D94e59332732D18CF3a3D457A8886A2AE29eA1B",
            "CAND": "0x70Ad7172EF0b131A1428D0c1F66457EB041f2176",
            "CNYX": "0x8d32E20d119d936998575B4AAff66B9999011D27", #Deflationary (like 10 %)
            "dFLR": "0x6f1Be01f9cD0c14E38f94E81Cb281ecB98Cc6A9b",
            "CGLD": "0x1c7d1dd0995dd0ABdd71FD67924C9dD4Cf7b4135",
            "PSB": "0xb2987753D1561570f726Aa373F48E77e27aa5FF4",
            "sRIBBITS": "0x399E279c814a3100065fceaB8CbA1aB114805344",
            "TRSH": "0x43344Ced39E2d7a6Be7Eda306E1750747D9Dcb01",
        }

        mr_const = 200
        min_reserve = {
            "WSGB": mr_const,
            "SFORT": mr_const,
            "DOOD": mr_const,
            "sDOOD": mr_const,
            "ORACLE": mr_const,
            "xORACLE": mr_const,
            "PRO": mr_const, #Deflationary (1%)
            "HS": mr_const,
            "EXFI": mr_const,
            "SFIN": mr_const / 10000,
            "CAND": mr_const,
            "CNYX": mr_const, #Deflationary (like 10 %)
            "dFLR": mr_const,
            "CGLD": mr_const,
            "PSB": mr_const,
            "sRIBBITS": mr_const * 1000,
            "TRSH": mr_const,
        }
        deflationary_tokens = ['0x8d32E20d119d936998575B4AAff66B9999011D27',
                              '0xf810576A68C3731875BDe07404BE815b16fC0B4e'] # Songbird
        exchanges = ["oracleswap", "pangolin", "blazeswap"]
        source_tokens = ["WSGB"]

