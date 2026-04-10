# FlashArb OpenClaw Deployment

This runbook is for deploying `FlashArb` onto a server that OpenClaw will manage.

## Goal

Run FlashArb continuously as a Moltbook-native X Layer arbitrage agent with:

1. live quote scanning
2. real onchain execution
3. periodic Moltbook posting
4. automatic restart

## Prerequisites

- Node.js already installed
- Python 3 available
- `git`, `curl`, `systemd`
- a logged-in Agentic Wallet session or a dedicated private key
- OKX Dev Portal credentials
- Moltbook API key

## Clone

```bash
git clone https://github.com/richard7463/flasharb-xlayer-arbitrage-bot.git
cd flasharb-xlayer-arbitrage-bot/dexfight
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Environment

Create `.env`:

```env
ONCHAINOS_API_KEY=...
ONCHAINOS_API_SECRET=...
ONCHAINOS_API_PASSPHRASE=...
ONCHAINOS_CHAIN_INDEX=196
ONCHAINOS_TIMEOUT=20
ONCHAINOS_PROXY=http://127.0.0.1:7890

FLASHARB_EXECUTION_BACKEND=agentic
FLASHARB_MODE=live
FLASHARB_BASE_TOKEN=auto
FLASHARB_BASE_TOKENS=USDT0,USDC,USDT
FLASHARB_TOKENS=OKB,USDC,WBTC
FLASHARB_DEXES=uniswap,quickswap,revoswap,okie
TRADE_AMOUNT_USD=1
FLASHARB_MIN_PROFIT_USD=0.05
FLASHARB_MIN_SPREAD_PCT=0.30
FLASHARB_MAX_PRICE_IMPACT_PCT=2.00
FLASHARB_SLIPPAGE_PERCENT=0.50
FLASHARB_MAX_TRADES_PER_HOUR=10
FLASHARB_MAX_DAILY_LOSS_USD=20
FLASHARB_RATE_LIMIT_COOLDOWN_SEC=180
FLASHARB_IDLE_PROBE_ENABLED=true
FLASHARB_IDLE_PROBE_TOKEN=OKB
FLASHARB_IDLE_PROBE_AMOUNT_USD=0.10
FLASHARB_IDLE_PROBE_INTERVAL=900
CHECK_INTERVAL=45
FLASHARB_LOG_DIR=logs
FLASHARB_REPO_URL=https://github.com/richard7463/flasharb-xlayer-arbitrage-bot

WALLET_ADDRESS=<agentic-wallet-evm-address>
RPC_URL=https://rpc.xlayer.com

MOLTBOOK_API_KEY=...
MOLTBOOK_PROXY=http://127.0.0.1:7890
MOLTBOOK_SUBMOLT=buildx
MOLTBOOK_MOCK_MODE=false
MOLTBOOK_POST_INTERVAL=180
```

## Install OnchainOS CLI

```bash
npx skills add okx/onchainos-skills -y
curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
onchainos --version
```

## Login Agentic Wallet

```bash
export PATH="$HOME/.local/bin:$PATH"
set -a && source .env && set +a
export HTTPS_PROXY=${ONCHAINOS_PROXY:-http://127.0.0.1:7890} HTTP_PROXY=${ONCHAINOS_PROXY:-http://127.0.0.1:7890}

onchainos wallet status
onchainos wallet login <owner-email> --locale en-US
onchainos wallet verify <otp>
onchainos wallet balance --force
```

## Smoke Test

```bash
. .venv/bin/activate
set -a && source .env && set +a
python run.py --once
```

Then try one live cycle only when wallet has funds:

```bash
. .venv/bin/activate
set -a && source .env && set +a
python run.py --live --once
```

## systemd Service

`/etc/systemd/system/flasharb.service`

```ini
[Unit]
Description=FlashArb X Layer arbitrage agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/flasharb-xlayer-arbitrage-bot/dexfight
Environment=HOME=/home/ubuntu
ExecStart=/bin/bash -lc '. .venv/bin/activate && set -a && source .env && set +a && export PATH="$HOME/.local/bin:$PATH" && export HTTPS_PROXY=${ONCHAINOS_PROXY:-http://127.0.0.1:7890} HTTP_PROXY=${ONCHAINOS_PROXY:-http://127.0.0.1:7890} && python run.py --live'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now flasharb.service
```

## What OpenClaw Should Verify

```bash
systemctl status flasharb.service --no-pager
tail -n 50 logs/flasharb_events.jsonl
onchainos wallet balance --force
```

OpenClaw should confirm:

1. base token auto-selects to `USD₮0` when `0x779ded0c9e1022225f8e0630b35a9b54be713736` has the highest stable balance, even if OKX returns that token as `USDT`
2. live cycles produce `buy_tx_hash` and `sell_tx_hash`
3. Moltbook posts continue appearing for the FlashArb agent
4. no repeated approval failures or exhausted gas balance
5. the runtime cools down after OKX API `429` responses instead of hammering the quote API
6. no duplicate `--once` posts causing Moltbook `429` rate-limit errors
7. `idle probe` only triggers when no profitable spread exists, and still records both tx hashes

## OpenClaw Prompt

> Deploy `FlashArb` from `https://github.com/richard7463/flasharb-xlayer-arbitrage-bot` on this server. Use the provided `.env`, install the Python dependencies, install the OnchainOS CLI and skills, verify the Agentic Wallet login, run `python run.py --once` as a smoke test, then install a `systemd` service that runs `python run.py --live` continuously. Confirm that the runtime uses `USD₮0` as the base asset when funded, scans `uniswap,quickswap,revoswap,okie`, backs off after OKX `429` responses, and verify Moltbook posting plus recent tx hashes in `logs/flasharb_events.jsonl`.
