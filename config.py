# XLayer Arbitrage Bot Configuration

# Wallet
WALLET_ADDRESS = "0xYourWalletAddressHere"

# Trading Settings
MIN_SPREAD = 0.5  # Minimum spread percentage to execute trade
TRADE_AMOUNT = 100  # USDC amount per trade

# Monitoring
CHECK_INTERVAL = 60  # Seconds between checks
TOKENS_TO_MONITOR = [
    "WIF/USDC",
    "PEPE/USDC",
    "SHIB/USDC",
    "GIGA/USDC",
    "NEIRO/USDC",
]

# Risk Management
MAX_GAS_PRICE = 50  # Max gas price in Gwei
STOP_LOSS = 10  # Stop trading if losing X%

# Logging
LOG_FILE = "arbitrage.log"
MOLTBOOK_ENABLED = True
TWITTER_ENABLED = True

# X Layer
XLAYER_CHAIN_ID = 19697  # X Layer testnet: 19697, mainnet: 196
XLAYER_RPC = "https://rpc.xlayer.com"

# Quote Token
QUOTE_TOKEN = "USDC"
