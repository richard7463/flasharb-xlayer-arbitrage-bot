"""
Monitor - Price monitoring for multiple DEXes
Adapted for X Layer
"""

import asyncio
import datetime
import calendar
import os
import json
import logging
import csv
from typing import List, Dict

import web3dex
from config_xlayer import CHAIN, MIN_GAP, MIN_LIQUIDITY

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for monitoring"""

    def __init__(self, input_token, output_token, routing, min_gap, min_liquidity, timeout, daemon, dexes):
        self.chain = CHAIN["name"].lower()
        self.input = input_token  # Input token (None = base)
        self.output = output_token  # Output token
        self.routing = routing
        self.min_gap = min_gap
        self.min_liquidity = min_liquidity
        self.timeout = timeout
        self.daemon = daemon
        self.dexes = dexes

        # For logging
        self.log_file = "xlayer_monitor.log"
        self.csv_file = "xlayer_gaps.csv"

    @staticmethod
    def read(conf_file: str) -> 'Config':
        """Read config from JSON file"""
        with open(conf_file) as f:
            data = json.load(f)

        return Config(
            input_token=data.get('input'),
            output_token=data.get('output'),
            routing=data.get('routing'),
            min_gap=data.get('min_gap', MIN_GAP),
            min_liquidity=data.get('min_liquidity', MIN_LIQUIDITY),
            timeout=data.get('timeout', 30),
            daemon=data.get('daemon', True),
            dexes=data.get('dexes', "uniswap_v3,sushiswap,pancakeswap,okx")
        )


async def looper(config_file: str = None):
    """Main looper"""
    if config_file:
        conf = Config.read(config_file)
    else:
        # Use default X Layer config
        conf = Config(
            input_token=None,  # USDC
            output_token="WIF",  # WIF token
            routing=None,
            min_gap=MIN_GAP,
            min_liquidity=MIN_LIQUIDITY,
            timeout=30,
            daemon=True,
            dexes="uniswap_v3,sushiswap,pancakeswap,okx"
        )

    file_handler = logging.FileHandler(filename=conf.log_file)
    stdout_handler = logging.StreamHandler()

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        handlers=[file_handler, stdout_handler]
    )

    while True:
        try:
            await main(conf)
        except Exception as err:
            logger.error(f"Error: {err}")
        finally:
            if not conf.daemon:
                return
            await asyncio.sleep(conf.timeout)


async def main(conf: Config) -> List[Dict]:
    """Main monitoring function"""
    values = {}

    # Get block number
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(CHAIN["rpc_url"]))
        block_number = w3.eth.block_number
        logger.info(f"Block: {block_number}")
    except Exception as e:
        logger.warning(f"Could not get block number: {e}")
        block_number = 0

    # Scan each DEX
    for DexClass in web3dex.all[conf.chain]:
        dex = DexClass(CHAIN["rpc_url"])

        if dex.platform not in conf.dexes.split(','):
            continue

        input_token = conf.input if conf.input else dex.base_address
        output_token = conf.output if conf.output else dex.token

        if dex.exist(input_token, output_token):
            value = dex_read(dex, input_token, output_token)

            # Check liquidity thresholds
            if (value['liquidity_in'] > conf.min_liquidity and
                value['price'] != 0 and
                value['liquidity_out'] > conf.min_liquidity * value['price']):
                values[dex.platform] = value
                logger.info(f"{dex.platform}: price={value['price']:.6f}, liq_in={value['liquidity_in']:.0f}")

    # Find gaps
    gaps = []
    for k, v in values.items():
        for kk, vv in values.items():
            if k == kk:
                continue

            gap = (v['reserve_ratio'] - vv['reserve_ratio']) / v['reserve_ratio']

            if gap > conf.min_gap:
                now = datetime.datetime.now()
                out = {
                    "timestamp": calendar.timegm(now.utctimetuple()),
                    "timestamp_iso": now.isoformat(),
                    "block": block_number,
                    "chain": CHAIN["name"],
                    "chain_id": CHAIN["chain_id"],
                    "gap": gap,
                    "gap_pct": f"{gap * 100:.2f}%",
                }

                # Add DEX0 info
                dex0_info = dict(map(lambda kv: ('dex0_' + kv[0], kv[1]), v.items()))
                out = {**out, **dex0_info}

                # Add DEX1 info
                dex1_info = dict(map(lambda kv: ('dex1_' + kv[0], kv[1]), vv.items()))
                out = {**out, **dex1_info}

                # Log
                text = f"GAP: {gap*100:.2f}% | {k} vs {kk} | {v['price']:.6f} vs {vv['price']:.6f}"
                logger.info(text)

                # Save to CSV
                append_csv(conf.csv_file, out)
                gaps.append(out)

    return gaps


def dex_read(dex, input_token, output_token, intermediate=None) -> Dict:
    """Read data from DEX"""
    return {
        'platform': dex.platform,
        'price': dex.price(input_token, output_token, intermediate),
        'reserve_ratio': dex.reserve_ratio(input_token, output_token, intermediate, refresh=True),
        'liquidity_in': dex.liquidity_in(input_token, output_token, intermediate),
        'liquidity_out': dex.liquidity_out(input_token, output_token, intermediate),
        'fees': dex.fees(input_token, output_token, intermediate),
    }


def append_csv(file: str, data: Dict):
    """Append data to CSV file"""
    file_exists = os.path.exists(file)

    with open(file, 'a', newline='') as f:
        writer = csv.writer(f)

        if not file_exists:
            # Write header
            header = list(data.keys())
            writer.writerow(header)

        # Write row
        row = list(data.values())
        writer.writerow(row)


if __name__ == "__main__":
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(looper(config_file))
