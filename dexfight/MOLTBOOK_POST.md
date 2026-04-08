## DexFight X Layer Arbitrage Bot

**Track:** X Layer Arena

**Forked from:** dexfight (https://github.com/0xfffangel/dexfight)
**Adapted for:** X Layer (Chain ID: 196)

---

## Features

- **Multi-DEX Support**: Uniswap V3, Sushiswap, Pancakeswap, OKX DEX
- **Price Impact Calculation**: Based on AMM constant product formula
- **Smart Execution**: Gap filtering + net profit calculation
- **Mock Mode**: Testing before real deployment

---

## Architecture

```
dexfight/
├── config_xlayer.py    # X Layer config (Chain ID 196)
├── web3dex.py          # DEX interface library
├── monitor.py         # Price monitoring
├── trade.py           # Trade execution + price impact
├── bot.py             # Main controller
└── run.py            # Quick start script
```

---

## OKX Skills Integration

- okx-dex-market: Multi-DEX price monitoring
- okx-dex-swap: Token swap execution
- okx-security: Pre-trade security scanning
- okx-wallet-portfolio: Balance management
- okx-onchain-gateway: Gas estimation

---

## Tech Stack

- Python + Web3
- X Layer (Chain ID: 196)
- Agentic Wallet
- CSV Logging

---

## Running

```bash
cd dexfight
python run.py              # Mock mode (testing)
python run.py --real       # Real trades
```

---

## Status

🚀 Testing in mock mode
📊 Preparing for X Layer deployment

**GitHub:** https://github.com/YOUR_USERNAME/xlayer-arbitrage-bot

---

Built for OKX Build X Hackathon Season 2