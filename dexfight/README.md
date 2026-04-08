# DexFight X Layer - Arbitrage Bot

AI-powered cross-DEX arbitrage trading agent for X Layer.

Forked from [dexfight](https://github.com/0xfffangel/dexfight) and adapted for X Layer network with OKX Onchain OS Skills integration.

## Features

- **Multi-DEX Support**: Uniswap V3, Sushiswap, Pancakeswap, OKX DEX
- **Price Impact Calculation**: Based on AMM constant product formula
- **Smart Trade Execution**: Buy low → Sell high with gap filtering
- **X Layer Native**: Built for X Layer (Chain ID: 196)
- **CSV Logging**: Track all opportunities and trades

## Architecture

```
dexfight/
├── config_xlayer.py    # X Layer chain configuration
├── web3dex.py        # DEX interface library
├── monitor.py        # Price monitoring + opportunity discovery
├── trade.py         # Trade execution + price impact
├── bot.py           # Main controller
└── config.json     # Configuration
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure wallet (edit wallets/xlayer.json with your private key)
echo '{"wallet_address":"0x...","private_key":"0x...","amount":100,"min_gap":0.01}' > wallets/xlayer.json

# Run once
python bot.py --once -t WIF

# Run daemon
python bot.py --daemon -t WIF
```

## Configuration

Edit `config.json`:
```json
{
  "chain": "xlayer",
  "input": null,
  "output": "WIF",
  "min_gap": 0.01,
  "min_liquidity": 10000,
  "timeout": 30,
  "daemon": true,
  "dexes": "uniswap_v3,sushiswap,pancakeswap,okx"
}
```

## Environment Variables

- `PRIVATE_KEY`: Wallet private key
- `WALLET_ADDRESS`: Wallet address
- `AMOUNT`: Trade amount in USDC
- `MIN_GAP`: Minimum spread (e.g., 0.01 = 1%)

## OKX Skills Integration

This project uses OKX Onchain OS Skills:
- `okx-dex-market`: Multi-DEX price monitoring
- `okx-dex-swap`: Token swap execution
- `okx-security`: Pre-trade security scanning
- `okx-wallet-portfolio`: Balance management

## Chain Info

- **Network**: X Layer
- **Chain ID**: 196 (mainnet)
- **RPC**: https://rpc.xlayer.com
- **Explorer**: https://www.okx.com/explorer/xlayer

## License

MIT

## Credits

- Original dexfight: https://github.com/0xfffangel/dexfight
- X Layer: https://xlayer.com
- OKX: https://okx.com