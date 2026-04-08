"""
Core Arbitrage Logic
Find and execute arbitrage opportunities with proper risk management
"""

import time
import logging
from typing import Dict, Optional
from skills.dex_market import DexMarketSkill
from skills.dex_swap import DexSwapSkill
from skills.security import SecuritySkill
from skills.wallet import WalletSkill

logger = logging.getLogger(__name__)


class ArbitrageEngine:
    """Core arbitrage detection and execution engine"""

    def __init__(self, config: Dict):
        self.config = config
        self.wallet = WalletSkill(config["private_key"], config["rpc_url"])
        self.market = DexMarketSkill(config["rpc_url"], config.get("okx_api_key", ""))
        self.swap = DexSwapSkill(config["private_key"], config["rpc_url"])
        self.security = SecuritySkill(config.get("security_api_key", ""))

        # Slippage settings
        self.default_slippage = config.get("slippage", 0.5)
        self.max_slippage = config.get("max_slippage", 2.0)

        # Latency settings
        self.max_latency_ms = config.get("max_latency_ms", 5000)
        self.price_staleness_seconds = config.get("price_staleness", 30)

    def find_opportunities(self, token_pairs: list) -> list:
        """Find arbitrage opportunities for multiple pairs"""
        opportunities = []

        for pair in token_pairs:
            opp = self.market.find_arbitrage(pair)
            if opp.get("found") and opp["spread"] >= self.config["min_spread"]:
                # Calculate profit after gas
                estimated_gas = self.estimate_gas_cost(opp)
                net_spread = opp["spread"] - estimated_gas

                if net_spread >= self.config["min_spread"]:
                    opportunities.append({
                        "pair": pair,
                        "spread": opp["spread"],
                        "net_spread": net_spread,
                        "buy_dex": opp["buy_dex"],
                        "sell_dex": opp["sell_dex"],
                        "min_price": opp["min_price"],
                        "max_price": opp["max_price"],
                        "timestamp": time.time(),
                    })

        return opportunities

    def estimate_gas_cost(self, opportunity: Dict) -> float:
        """
        Estimate gas cost as percentage of trade

        Args:
            opportunity: The arbitrage opportunity

        Returns:
            Gas cost as percentage
        """
        # Average gas for 2 swaps: ~300k gas each
        # Assuming 50 gwei gas price, XLM ~$0.001
        gas_units = 300000 * 2
        gas_price_gwei = 50
        xlm_price = 0.001  # Estimate

        # Trade value
        trade_value = self.config["trade_amount"]

        # Gas cost in USD
        gas_cost_usd = (gas_units * gas_price_gwei * 1e-9) * xlm_price

        # As percentage
        gas_percentage = (gas_cost_usd / trade_value) * 100

        return gas_percentage

    def calculate_dynamic_slippage(self, spread: float, latency_ms: int) -> float:
        """
        Calculate slippage based on market conditions

        Args:
            spread: Current spread percentage
            latency_ms: Expected latency in milliseconds

        Returns:
            Recommended slippage tolerance
        """
        base_slippage = self.default_slippage

        # Increase slippage for larger spreads (more room for price movement)
        spread_multiplier = min(spread / 5.0, 1.5)

        # Increase slippage for higher latency
        latency_multiplier = 1 + (latency_ms / self.max_latency_ms)

        final_slippage = base_slippage * spread_multiplier * latency_multiplier

        # Cap at max
        return min(final_slippage, self.max_slippage)

    def validate_prices_not_stale(self, opportunity: Dict) -> bool:
        """
        Check if prices are still valid (not stale)

        Args:
            opportunity: The opportunity to validate

        Returns:
            True if prices are fresh enough
        """
        age = time.time() - opportunity.get("timestamp", 0)
        return age < self.price_staleness_seconds

    def simulate_trade(self, opportunity: Dict) -> Dict:
        """
        Simulate trade to check if it will succeed

        Args:
            opportunity: The arbitrage opportunity

        Returns:
            Simulation result with expected outcomes
        """
        pair = opportunity["pair"]
        token = pair.split("/")[0]

        # Estimate latency
        start = time.time()
        quote = self.swap.get_quote(
            self.config["quote_token"],
            token,
            self.config["trade_amount"],
            opportunity["buy_dex"]
        )
        latency_ms = (time.time() - start) * 1000

        if latency_ms > self.max_latency_ms:
            return {
                "can_proceed": False,
                "reason": f"Latency too high: {latency_ms}ms",
                "latency_ms": latency_ms
            }

        # Calculate dynamic slippage
        slippage = self.calculate_dynamic_slippage(opportunity["spread"], latency_ms)

        # Check if quote is acceptable
        expected_out = quote * (1 - slippage / 100)
        min_profitable = self.config["trade_amount"] * (1 + self.config["min_spread"] / 100)

        return {
            "can_proceed": expected_out >= min_profitable,
            "quote": quote,
            "expected_out": expected_out,
            "slippage": slippage,
            "latency_ms": latency_ms,
            "min_profitable": min_profitable,
        }

    def execute_arbitrage(self, opportunity: Dict) -> Dict:
        """Execute single arbitrage trade with proper slippage handling"""
        pair = opportunity["pair"]
        token = pair.split("/")[0]

        # Step 1: Security scan
        security = self.security.scan(token)
        if security["risk_level"] != "low" or security.get("honeypot"):
            logger.warning(f"[SECURITY] {token} failed security check")
            return {"success": False, "reason": "failed_security", "details": security}

        # Step 2: Check balance
        if not self.wallet.ensure_sufficient_balance(
            self.config["quote_token"],
            self.config["trade_amount"]
        ):
            return {"success": False, "reason": "insufficient_balance"}

        # Step 3: Validate prices not stale
        if not self.validate_prices_not_stale(opportunity):
            return {"success": False, "reason": "prices_stale"}

        # Step 4: Simulate trade first
        simulation = self.simulate_trade(opportunity)
        if not simulation.get("can_proceed"):
            logger.warning(f"[SIMULATION] {simulation.get('reason')}")
            return {"success": False, "reason": "simulation_failed", "details": simulation}

        # Step 5: Get dynamic slippage
        slippage = simulation["slippage"]

        # Step 6: Execute buy with calculated slippage
        buy_result = self.swap.execute_swap(
            self.config["quote_token"],
            token,
            self.config["trade_amount"],
            opportunity["buy_dex"],
            slippage=slippage
        )

        if buy_result["status"] != "success":
            return {"success": False, "reason": "buy_failed", "details": buy_result}

        # Step 7: Wait minimal time and execute sell immediately
        # Use tighter slippage for sell as price may have moved
        sell_slippage = slippage * 0.5  # Tighter slippage

        sell_result = self.swap.execute_swap(
            token,
            self.config["quote_token"],
            buy_result["amount_out"],
            opportunity["sell_dex"],
            slippage=sell_slippage
        )

        # Calculate actual profit
        final_amount = sell_result.get("amount_out", 0)
        cost = self.config["trade_amount"]
        profit = final_amount - cost
        profit_percentage = (profit / cost) * 100

        return {
            "success": sell_result["status"] == "success",
            "buy_tx": buy_result["tx_hash"],
            "sell_tx": sell_result["tx_hash"],
            "profit": profit,
            "profit_percentage": profit_percentage,
            "slippage_used": slippage,
            "amount_out": final_amount,
            "details": {
                "buy": buy_result,
                "sell": sell_result,
                "simulation": simulation,
            }
        }
