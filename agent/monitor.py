"""
Price Monitor Module
Continuous price monitoring across DEXes
"""

import time
from typing import Dict, List
from skills.dex_market import DexMarketSkill


class PriceMonitor:
    """Monitor prices and detect opportunities"""

    def __init__(self, config: Dict):
        self.config = config
        self.market = DexMarketSkill(config["rpc_url"])
        self.last_opportunities = []

    def check_all_pairs(self, token_pairs: List[str]) -> List[Dict]:
        """Check all token pairs for opportunities"""
        opportunities = []

        for pair in token_pairs:
            opp = self.market.find_arbitrage(pair)

            if opp.get("found") and opp["spread"] >= self.config["min_spread"]:
                opportunities.append({
                    "pair": pair,
                    "spread": opp["spread"],
                    "buy_dex": opp["buy_dex"],
                    "sell_dex": opp["sell_dex"],
                    "min_price": opp["min_price"],
                    "max_price": opp["max_price"],
                    "timestamp": time.time()
                })

        self.last_opportunities = opportunities
        return opportunities

    def start_monitoring(self):
        """Start continuous monitoring loop"""
        print(f"[Monitor] Starting monitoring for {len(self.config['tokens'])} pairs")

        while True:
            opportunities = self.check_all_pairs(self.config["tokens"])

            if opportunities:
                print(f"[Monitor] Found {len(opportunities)} opportunities")
                for opp in opportunities:
                    print(f"  - {opp['pair']}: {opp['spread']:.2f}% spread")
            else:
                print(f"[Monitor] No opportunities found")

            time.sleep(self.config["check_interval"])
