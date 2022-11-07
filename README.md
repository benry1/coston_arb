# coston_arb

Naive circular arb implementation, assuming UNISWAP v2 style contracts.

Credit @ccyanxyz for the math around optimal swap amounts: `https://github.com/ccyanxyz/uniswap-arbitrage-analysis` \
Credit @qpwo for the Johnson's Algorithm implementation `https://github.com/qpwo/python-simple-cycles`


## What's up with this graph structure?

This implementation is a workaround because the Johnson algorithm does NOT support multiple edges between the same node. So, isntead of having one WNAT <-> Token2 edge for each exchange, we actually need to create a new node. \

Each node holds two pieces of information, ("Exchange", "tokenAddress"), and this means trade for TokenAddress using Exchange. \

So. There is a "Source" node, which is unaffiliated to an exchange, and represents what is held on the contract. The "Source" node has edges to every (Exchange, Token) node where a pool exists for that swap. \

In addition to the ("Source", "sourceToken") nodes, there are also ("Exchange", "sourceToken") nodes for each exchange. These (Exchange, sourceToken) nodes ONLY have edges to ("Source", token), because once you use an exchange to swap for your source token, you have completed the cycle. \\

Every cycle will have this form: \\

` ('source', 'sourceTokenAddress') -> ("exchange1", "token1") -> ... -> ("exchangeN-1", "tokenN-1") -> ("exchange", sourceTokenAddress) -> ('source', 'sourceTokenAddress') `