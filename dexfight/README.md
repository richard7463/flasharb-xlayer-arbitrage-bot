# FlashArb - Moltbook-Native X Layer Arbitrage Agent

FlashArb is an X Layer trading agent for the OKX Build X hackathon. The runtime now uses the official OKX Onchain OS DEX API for:
- live token discovery
- live liquidity-source discovery
- per-DEX quote scanning
- approval + swap transaction generation
- Moltbook status posting
- Agentic Wallet execution when no private key is provided

This repo should be read as a **real execution runtime**, not a mock dashboard. Recent tx hashes, execution checkpoints, and route-health posts are part of the public proof loop.

The old `bot.py` / `monitor.py` / `trade.py` flow is still in the repo as legacy code from the original `dexfight` fork. The current entrypoint for the hackathon agent is [`run.py`](./run.py).

## What Changed

The original project had three blocking problems for the agent track:
- `run.py --real` only printed `Would execute ...`
- `skills_xlayer.py` returned `status=simulated`
- `web3dex.py` used mock reserves

The current runtime fixes the first two by moving scanning and execution onto the official OKX DEX endpoints. `web3dex.py` remains only for the older legacy path.

## Runtime Model

`run.py` now behaves like a real agent loop:
1. Resolve supported X Layer tokens from Onchain OS
2. Auto-select the strongest funded stable base asset, prioritizing `USD₮0 -> USDC -> USDT`
3. Resolve available liquidity sources such as Uniswap, QuickSwap, Revoswap, and Okie on X Layer
4. Quote `stable -> token` on one DEX and `token -> stable` on another DEX
5. Rank opportunities by estimated net profit after quote fees
6. In `paper` mode: log and post results only
7. In `live` mode:
   - `private-key` backend signs directly through RPC
   - `agentic` backend executes through `onchainos swap execute`
8. If no spread clears thresholds, optional `idle probe` can still execute a tiny round-trip for tx proof and route health checks
9. Post updates to Moltbook with recent tx hashes

The X Layer stable at `0x779ded0c9e1022225f8e0630b35a9b54be713736` is treated as `USD₮0` in this repo even when some OKX endpoints label it as `USDT`.

## Install

```bash
cd dexfight
pip install -r requirements.txt
cp .env.example .env
```

## Required Environment Variables

```dotenv
ONCHAINOS_API_KEY=...
ONCHAINOS_API_SECRET=...
ONCHAINOS_API_PASSPHRASE=...
WALLET_ADDRESS=0x...
```

Optional but recommended:

```dotenv
FLASHARB_EXECUTION_BACKEND=agentic
FLASHARB_BASE_TOKEN=auto
FLASHARB_BASE_TOKENS=USDT0,USDC,USDT
RPC_URL=https://rpc.xlayer.com
PRIVATE_KEY=0x... # only needed for private-key backend
MOLTBOOK_API_KEY=...
MOLTBOOK_PROXY=
FLASHARB_TOKENS=OKB,USDC,WBTC
FLASHARB_DEXES=uniswap,quickswap,revoswap,okie
TRADE_AMOUNT_USD=1
FLASHARB_MIN_PROFIT_USD=0.05
FLASHARB_MIN_SPREAD_PCT=0.30
FLASHARB_RATE_LIMIT_COOLDOWN_SEC=180
FLASHARB_IDLE_PROBE_ENABLED=true
FLASHARB_IDLE_PROBE_TOKEN=OKB
FLASHARB_IDLE_PROBE_AMOUNT_USD=0.10
FLASHARB_IDLE_PROBE_INTERVAL=900
MOLTBOOK_POST_INTERVAL=180
```

## Run

Paper mode, one cycle:

```bash
python3 run.py --once
```

Paper mode, continuous:

```bash
python3 run.py
```

Live mode, real approvals and swaps:

```bash
python3 run.py --live
```

If you use Agentic Wallet instead of a raw private key:

```bash
export PATH="$HOME/.local/bin:$PATH"
onchainos wallet status
```

The wallet must already be logged in before `--live` mode starts.

## Moltbook

Register and claim the agent first:

```bash
python3 moltbook_register.py --name FlashArb --owner-x your_x_handle
```

Post manually or let the runtime post periodic updates:

```bash
MOLTBOOK_API_KEY=your_key python3 moltbook_poster.py
```

`run.py` automatically calls `moltbook_poster.py` logic when `MOLTBOOK_API_KEY` is configured.
When live tx growth pauses, the poster now emits **live ops checkpoints** instead of repeating the same execution title.

## Logs

The runtime writes structured events to:

```text
logs/flasharb_events.jsonl
```

That file is useful for:
- tx proof collection
- Moltbook update summaries
- demo video narration
- judging evidence

## Agent-Track Positioning

FlashArb should be positioned as a **Moltbook-native execution agent**, not just a background bot:
- it scans live X Layer liquidity via Onchain OS
- it can execute real approvals and swaps
- it can execute through Agentic Wallet, which fits the hackathon's required onchain identity model
- it persists an audit trail
- it can post its own state back to Moltbook
- it now backs off automatically after OKX API `429` responses instead of hammering the quote API
- it can keep posting route-health / cooldown / execution posture updates even between new tx milestones

For the hackathon, this makes it much stronger for `Most active agent` than the earlier mock version.

## Open-Source References

Strong public references worth studying:
- [AgentHedge](https://github.com/anilkaracay/AgentHedge)
- [TriMind Agent](https://github.com/satoshinakamoto666666/trimind-agent)
- [xlayer-agentic-vault](https://github.com/pablomg-dev/xlayer-agentic-vault)
- [xlayer-defi-agent](https://github.com/Batman0506/xlayer-defi-agent)
- [official OKX Build X agent skill](https://github.com/okx/plugin-store/tree/main/skills/okx-buildx-hackathon-agent-track)
- [Moltbook skill](https://www.moltbook.com/skill.md)

## Known Limits

This is now execution-ready plumbing, but not yet a finished champion build:
- it still needs a hardened deployment target for 24/7 operation
- it does not yet ingest Moltbook mentions as trading commands
- it assumes your OKX API credentials, Agentic Wallet session, and token universe are valid on X Layer
- the legacy `web3dex.py` path is still in the repo and should not be treated as the main runtime
- with very small capital, most cycles will either idle or fall back to the optional probe path
- on servers with direct outbound access, leave `ONCHAINOS_PROXY` and `MOLTBOOK_PROXY` empty
