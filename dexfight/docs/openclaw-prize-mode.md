# FlashArb OpenClaw Prize Mode

Use this exact environment on OpenClaw for the current prize run:

```env
FLASHARB_EXECUTION_BACKEND=agentic
FLASHARB_MODE=live
FLASHARB_BASE_TOKEN=auto
FLASHARB_BASE_TOKENS=USDT0,USDC,USDT
FLASHARB_TOKENS=OKB
FLASHARB_DEXES=uniswap,quickswap
TRADE_AMOUNT_USD=0.50
FLASHARB_MIN_PROFIT_USD=0.05
FLASHARB_MIN_SPREAD_PCT=0.30
FLASHARB_MAX_PRICE_IMPACT_PCT=2.00
FLASHARB_SLIPPAGE_PERCENT=0.50
FLASHARB_MAX_TRADES_PER_HOUR=6
FLASHARB_MAX_DAILY_LOSS_USD=5
FLASHARB_RATE_LIMIT_COOLDOWN_SEC=180
FLASHARB_IDLE_PROBE_ENABLED=true
FLASHARB_IDLE_PROBE_TOKEN=OKB
FLASHARB_IDLE_PROBE_AMOUNT_USD=0.05
FLASHARB_IDLE_PROBE_INTERVAL=900
CHECK_INTERVAL=300
MOLTBOOK_POST_INTERVAL=900
```

Intent:

1. keep real tx flowing
2. keep Moltbook posting flowing
3. cut probe bleed
4. avoid hitting OKX quote limits as hard

What OpenClaw should do:

1. `git pull origin main`
2. update `.env` to match the block above
3. ensure `MOLTBOOK_API_KEY` is the `flasharb` agent key, not `agentfightclub`
4. restart `flasharb.service`
5. verify new events in `logs/flasharb_events.jsonl`
6. report back the newest `buy_tx_hash`, `sell_tx_hash`, and Moltbook post URL
