"""
Bot - Main arbitrage bot controller
Adapted for X Layer
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path

import monitor
import trade
import web3dex
from config_xlayer import CHAIN, MIN_GAP

# Setup logging
log_file = 'xlayer_bot.log'
file_handler = logging.FileHandler(filename=log_file)
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=handlers
)

logger = logging.getLogger(__name__)

# Config directories
config_dir = 'configs'
wallet_dir = 'wallets'


async def looper():
    """Main loop"""
    while True:
        try:
            await main()
        except Exception as err:
            logger.error(f"Error: {err}")
            import traceback
            traceback.print_exc()
        finally:
            await asyncio.sleep(30)


async def main():
    """Main function"""
    # Load all config files
    config_path = Path(config_dir)
    config_path.mkdir(exist_ok=True)

    for config_file in config_path.glob('config_*.json'):
        try:
            conf = monitor.Config.read(str(config_file))
            gap = await monitorize(conf, config_file.name)

            if gap:
                await trading(conf, gap)
        except Exception as err:
            logger.error(f"Error processing {config_file}: {err}")


async def monitorize(conf: monitor.Config, filename: str) -> dict:
    """Monitor for gaps"""
    gaps = await monitor.main(conf)

    logger.info(f"> {filename}: {len(gaps)} gaps found")

    if len(gaps) == 0:
        return None

    # Find best gap
    max_gap = gaps[0]
    for gap in gaps:
        if gap['gap'] > max_gap['gap']:
            max_gap = gap

    logger.info(f"> Best gap: {max_gap['gap']*100:.2f}%")
    logger.info(f"> DEX: {max_gap.get('dex0_platform')} vs {max_gap.get('dex1_platform')}")

    return max_gap


async def trading(conf: monitor.Config, gap: dict):
    """Execute arbitrage trade"""
    if gap is None:
        return

    # Load wallet
    wallet_file = Path(wallet_dir) / f"{CHAIN['name'].lower()}.json"

    if not wallet_file.exists():
        logger.warning(f"Wallet file not found: {wallet_file}")
        # Use default/demo wallet
        wallet_data = {
            "wallet_address": os.getenv("WALLET_ADDRESS", "0x0000000000000000000000000000000000000000"),
            "private_key": os.getenv("PRIVATE_KEY", "0x0000000000000000000000000000000000000000000000000000000000000000"),
            "amount": float(os.getenv("AMOUNT", "100")),
            "min_gap": float(os.getenv("MIN_GAP", "0.01"))
        }
    else:
        with open(wallet_file) as f:
            wallet_data = json.load(f)

    # Find DEX instances
    dex0_instance = None
    dex1_instance = None

    for DexClass in web3dex.all[CHAIN['name'].lower()]:
        dex = DexClass(CHAIN["rpc_url"], wallet_data.get("private_key", ""))

        dex0_name = gap.get('dex0_platform', '').replace('_dexcoin', '')
        dex1_name = gap.get('dex1_platform', '').replace('_dexcoin', '')

        if dex.platform == dex0_name:
            dex0_instance = dex
        if dex.platform == dex1_name:
            dex1_instance = dex

    if not dex0_instance or not dex1_instance:
        logger.error("Could not find DEX instances")
        return

    # Execute trade
    await trade.main(
        wallet_address=wallet_data['wallet_address'],
        private_key=wallet_data['private_key'],
        dex0=dex0_instance,
        dex1=dex1_instance,
        amount=wallet_data.get('amount', 100),
        min_gap=wallet_data.get('min_gap', MIN_GAP),
        path0_inToken=conf.input,
        path0_outToken=conf.output,
        path0_middleToken=dex0_instance.token,
        path1_inToken=conf.input,
        path1_outToken=conf.output,
        path1_middleToken=dex1_instance.token,
    )


# ============================================================================
# CLI
# ============================================================================

def get_args():
    """Get command line arguments"""
    import argparse

    parser = argparse.ArgumentParser(description="DexFight X Layer Bot")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run continuously")
    parser.add_argument("--once", "-o", action="store_true", help="Run once")
    parser.add_argument("--config", "-c", type=str, help="Config file")
    parser.add_argument("--amount", "-a", type=float, help="Trade amount")
    parser.add_argument("--min-gap", "-g", type=float, help="Minimum gap")
    parser.add_argument("--token", "-t", type=str, help="Token to trade")
    parser.add_argument("--wallet", "-w", type=str, help="Wallet private key")

    return parser.parse_args()


async def run_once(token: str = None, amount: float = 100, min_gap: float = MIN_GAP):
    """Run once"""
    # Create config
    conf = monitor.Config(
        input_token=None,  # USDC
        output_token=token or "WIF",
        routing=None,
        min_gap=min_gap,
        min_liquidity=10000,
        timeout=30,
        daemon=False,
        dexes="uniswap_v3,sushiswap,pancakeswap,okx"
    )

    gaps = await monitor.main(conf)

    if gaps:
        logger.info(f"Found {len(gaps)} opportunities")
        for gap in gaps:
            logger.info(f"  {gap['gap']*100:.2f}% - {gap.get('dex0_platform')} vs {gap.get('dex1_platform')}")
    else:
        logger.info("No opportunities found")


async def run_daemon(token: str = None, amount: float = 100, min_gap: float = MIN_GAP):
    """Run as daemon"""
    conf = monitor.Config(
        input_token=None,
        output_token=token or "WIF",
        routing=None,
        min_gap=min_gap,
        min_liquidity=10000,
        timeout=30,
        daemon=True,
        dexes="uniswap_v3,sushiswap,pancakeswap,okx"
    )

    logger.info("=" * 60)
    logger.info("DexFight X Layer Bot Started")
    logger.info(f"Chain: {CHAIN['name']} (ID: {CHAIN['chain_id']})")
    logger.info(f"RPC: {CHAIN['rpc_url']}")
    logger.info(f"Token: {conf.output_token}")
    logger.info(f"Amount: {amount}")
    logger.info(f"Min Gap: {min_gap*100:.1f}%")
    logger.info("=" * 60)

    await looper()


if __name__ == "__main__":
    args = get_args()

    if args.daemon:
        asyncio.run(run_daemon(
            token=args.token,
            amount=args.amount or 100,
            min_gap=args.min_gap or MIN_GAP
        ))
    elif args.config:
        asyncio.run(looper())
    else:
        asyncio.run(run_once(
            token=args.token,
            amount=args.amount or 100,
            min_gap=args.min_gap or MIN_GAP
        ))
