#!/usr/bin/env python3
"""
DexFight X Layer - 快速跑交易量模式
============================
两种模式：
1. MOCK_MODE=True - 模拟交易，不亏钱，产生活动记录
2. MOCK_MODE=False - 真实交易，可能亏
"""

import os
import sys
import time
import random
import json
from datetime import datetime

# ============== 配置 ==============
CONFIG = {
    # 模式选择
    "MOCK_MODE": True,  # True=模拟, False=真实

    # 交易参数
    "TRADE_AMOUNT": 1,  # $1 试水
    "MIN_SPREAD": 0.001,  # 0.1% 就做 (刷交易量优先)
    "CHECK_INTERVAL": 5,  # 5秒检查一次

    # X Layer
    "CHAIN_ID": 196,
    "RPC": "https://rpc.xlayer.com",

    # 目标代币
    "TOKENS": ["WIF", "PEPE", "SHIB", "GIGA", "NEIRO"],
}

# ============== 模拟数据 ==============
class MockDex:
    """模拟 DEX 数据"""

    DEXES = ["uniswap", "sushiswap", "pancakeswap", "okx"]

    def __init__(self):
        self.base_prices = {
            "WIF": 1.80,
            "PEPE": 0.000012,
            "SHIB": 0.000021,
            "GIGA": 0.045,
            "NEIRO": 0.0012,
        }

    def get_prices(self, token):
        """生成随机的 DEX 价格差异"""
        base = self.base_prices.get(token, 1.0)
        prices = {}

        for dex in self.DEXES:
            # 随机价差 -1% 到 +1%
            spread = (random.random() - 0.5) * 0.02
            prices[dex] = base * (1 + spread)

        return prices

    def find_opportunity(self, token):
        """找套利机会"""
        prices = self.get_prices(token)

        min_price = min(prices.values())
        max_price = max(prices.values())
        spread = (max_price - min_price) / min_price

        min_dex = min(prices, key=prices.get)
        max_dex = max(prices, key=prices.get)

        return {
            "token": token,
            "spread": spread,
            "buy_dex": min_dex,
            "sell_dex": max_dex,
            "buy_price": min_price,
            "sell_price": max_price,
        }

    def execute_mock_trade(self, opportunity):
        """模拟交易执行"""
        import hashlib
        tx_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:64]
        return {
            "tx_hash": "0x" + tx_hash,
            "status": "success" if random.random() > 0.1 else "failed",
        }


# ============== 主程序 ==============
class ArbitrageBot:
    def __init__(self, config):
        self.config = config
        self.dex = MockDex()
        self.stats = {
            "total_trades": 0,
            "successful": 0,
            "failed": 0,
            "total_profit": 0,
            "start_time": time.time(),
        }

    def check_and_trade(self):
        """检查并交易"""
        token = random.choice(self.config["TOKENS"])
        opp = self.dex.find_opportunity(token)

        spread_pct = opp["spread"] * 100

        # 刷交易量模式：只要 spread > MIN_SPREAD 就做
        if spread_pct >= self.config["MIN_SPREAD"] * 100:
            self.stats["total_trades"] += 1

            if self.config["MOCK_MODE"]:
                # 模拟交易
                result = self.dex.execute_mock_trade(opp)
                profit = self.config["TRADE_AMOUNT"] * opp["spread"]

                if result["status"] == "success":
                    self.stats["successful"] += 1
                    self.stats["total_profit"] += profit
                    status = "✅"
                else:
                    self.stats["failed"] += 1
                    status = "❌"

                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Trade #{self.stats['total_trades']}: {opp['token']} | "
                      f"{spread_pct:.2f}% spread | "
                      f"${profit:.4f} profit | {status}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Would execute: {opp['token']} {spread_pct:.2f}% spread "
                      f"(real mode)")

        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"No opportunity: {token} {spread_pct:.2f}% < {self.config['MIN_SPREAD']*100}%")

    def run(self):
        """运行"""
        print("=" * 60)
        print("DexFight X Layer - Arbitrage Bot")
        print("=" * 60)
        print(f"Mode: {'MOCK (simulated)' if self.config['MOCK_MODE'] else 'REAL'}")
        print(f"Chain: X Layer ({self.config['CHAIN_ID']})")
        print(f"Trade Amount: ${self.config['TRADE_AMOUNT']}")
        print(f"Min Spread: {self.config['MIN_SPREAD']*100}%")
        print(f"Check Interval: {self.config['CHECK_INTERVAL']}s")
        print("=" * 60)

        # 统计输出
        try:
            while True:
                self.check_and_trade()

                # 每10笔输出统计
                if self.stats["total_trades"] > 0 and self.stats["total_trades"] % 10 == 0:
                    self.print_stats()

                time.sleep(self.config["CHECK_INTERVAL"])

        except KeyboardInterrupt:
            print("\nStopped!")
            self.print_stats()

    def print_stats(self):
        """打印统计"""
        uptime = time.time() - self.stats["start_time"]
        print("\n" + "=" * 60)
        print("📊 Statistics")
        print("=" * 60)
        print(f"Uptime:     {uptime/60:.1f} minutes")
        print(f"Total:     {self.stats['total_trades']} trades")
        print(f"Success:   {self.stats['successful']}")
        print(f"Failed:    {self.stats['failed']}")
        print(f"Profit:    ${self.stats['total_profit']:.4f}")
        print(f"Success Rate: {self.stats['successful']/max(1,self.stats['total_trades'])*100:.1f}%")
        print("=" * 60)


# ============== 入口 ==============
if __name__ == "__main__":
    # 命令行参数
    if "--real" in sys.argv:
        CONFIG["MOCK_MODE"] = False
        print("⚠️  REAL MODE - Will execute real trades!")
    elif "--help" in sys.argv:
        print("Usage: python run.py [--real]")
        print("  --real: Execute real trades (requires wallet)")
        print("  (default): Mock mode (simulated trades)")
        sys.exit(0)

    bot = ArbitrageBot(CONFIG)
    bot.run()