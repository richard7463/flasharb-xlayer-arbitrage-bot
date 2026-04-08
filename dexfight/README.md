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

## Moltbook Agent Claim Link

Moltbook 验证流程需要先注册 agent 并返回 claim link，再由人类发 X 推文完成 ownership verify。

```bash
cd dexfight
python moltbook_register.py --name FlashArb --owner-x your_x_handle
```

脚本会输出:
- 注册返回原始 JSON
- 自动提取的 `claim_link`
- 可直接复制的 X 验证推文模板

## Moltbook Real Posting

`moltbook_poster.py` 已接入 Moltbook 官方 API:
- `GET /api/v1/agents/status` (发帖前检查 `claimed`)
- `POST /api/v1/posts` (发布帖子到 `buildx`)
- `POST /api/v1/verify` (自动完成 challenge 验证)

示例:
```bash
cd dexfight
MOLTBOOK_API_KEY=your_key MOLTBOOK_PROXY=http://127.0.0.1:7890 python moltbook_poster.py
```

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
