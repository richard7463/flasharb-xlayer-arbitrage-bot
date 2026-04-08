# XLayer Arbitrage Bot 🤖

An autonomous AI agent that monitors DEX price differences on X Layer and executes profitable arbitrage trades automatically.

## 🎯 What It Does

- **Monitors** multiple DEXes on X Layer for price differences
- **Calculates** profit margins after gas costs
- **Executes** trades automatically when profitable
- **Protects** with pre-trade security scans
- **Logs** all activities on-chain

## 🛠️ Skills Used

| Skill | Usage |
|-------|-------|
| `okx-dex-market` | Multi-DEX price monitoring |
| `okx-dex-swap` | Token swap execution |
| `okx-security` | Pre-trade security scan |
| `okx-onchain-gateway` | Gas estimation & simulation |
| `okx-wallet-portfolio` | Balance check |

## 🚀 Quick Start

```bash
# Clone and install
git clone https://github.com/your-repo/xlayer-arbitrage-bot.git
cd xlayer-arbitrage-bot
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
python main.py
```

## 📁 Project Structure

```
xlayer-arbitrage-bot/
├── main.py                  # Entry point
├── config.py                # Configuration
├── requirements.txt         # Python dependencies
├── deploy.sh               # Deployment script
├── .env.example            # Environment template
├── README.md               # This file
├── agent/
│   ├── __init__.py
│   ├── arbitrage.py       # Core arbitrage logic
│   ├── security.py        # Security checks
│   ├── executor.py        # Trade execution
│   └── monitor.py         # Price monitoring
├── skills/
│   ├── __init__.py
│   ├── dex_market.py     # OKX DEX market skill
│   ├── dex_swap.py       # OKX DEX swap skill
│   ├── security.py       # OKX security skill
│   └── wallet.py         # OKX wallet skill
├── utils/
│   ├── __init__.py
│   ├── logger.py         # Logging utilities
│   ├── telegram.py       # Telegram notifications
│   └── moltbook.py      # Moltbook posting
└── tests/
    └── test_arbitrage.py
```

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Wallet
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=0xyour_wallet_address

# X Layer RPC
XLAYER_RPC=https://rpc.xlayer.com

# OKX API
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Moltbook
MOLTBOOK_API_KEY=your_moltbook_key
```

### Config File (`config.py`)

```python
# Wallet
WALLET_ADDRESS = "0x..."

# Trading Settings
MIN_SPREAD = 0.5  # Minimum 0.5% spread to execute trade
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

# X Layer
XLAYER_CHAIN_ID = 19697  # X Layer testnet
```

## 🎮 Commands

```bash
# Run once
python main.py --once

# Run continuously
python main.py --daemon

# Test mode (no real trades)
python main.py --test

# Check status
python main.py --status
```

## 🏗️ Architecture

### Agent Module (`agent/`)

- **arbitrage.py**: Core engine for finding and executing arbitrage
- **security.py**: Pre-trade security validation
- **executor.py**: Swap execution and gas estimation
- **monitor.py**: Continuous price monitoring

### Skills Module (`skills/`)

- **dex_market.py**: Multi-DEX price aggregation
- **dex_swap.py**: Token swap via DEX routers
- **security.py**: Token security scanning
- **wallet.py**: Balance and portfolio management

### Utils Module (`utils/`)

- **logger.py**: Structured logging
- **telegram.py**: Telegram alerts
- **moltbook.py**: Moltbook activity posting

## 📊 Features

### Core Features
- [x] Multi-DEX price monitoring
- [x] Automatic profit calculation
- [x] Gas cost analysis
- [x] Pre-trade security scan
- [x] On-chain transaction logging
- [x] Automatic trade execution

### Advanced Features
- [ ] Cross-chain arbitrage
- [ ] MEV protection
- [x] Telegram notifications
- [x] Moltbook posting
- [ ] Dashboard UI

## 🔒 Safety

- All trades require minimum spread threshold
- Security scan before every trade
- Max gas price protection
- Automatic stop-loss
- Transaction simulation before execution

## 📈 Stats

The bot tracks:
- Number of trades executed
- Total profit/loss
- Average spread captured
- Gas spent
- Uptime

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Or run directly
python tests/test_arbitrage.py
```

## 🤖 Agent Track

This project is designed for the X Layer Build X Hackathon Agent Track:

- Uses multiple Onchain OS Skills
- Operates autonomously on X Layer
- Generates real on-chain transactions
- Meets "Most Active Agent" criteria

## 📝 License

MIT

## 👤 Author

Your Name - @your_twitter

## 🙏 Thanks

- [OKX](https://okx.com) for Onchain OS
- [X Layer](https://xlayer.com) for the hackathon
