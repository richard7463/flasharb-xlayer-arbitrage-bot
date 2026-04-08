"""
Logging Utilities
Structured logging with timestamps
"""

import logging
import sys
from datetime import datetime


def setup_logger(name: str = "arbitrage-bot", level: int = logging.INFO):
    """Setup structured logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console.setFormatter(formatter)

    logger.addHandler(console)
    return logger


class TradeLogger:
    """Logger for trade events"""

    def __init__(self, log_file: str = "trades.log"):
        self.log_file = log_file

    def log_trade(self, trade_data: dict):
        """Log trade event"""
        timestamp = datetime.now().isoformat()
        entry = f"{timestamp} | {trade_data}\n"

        with open(self.log_file, "a") as f:
            f.write(entry)

    def log_opportunity(self, opp: dict):
        """Log found opportunity"""
        print(f"[OPPORTUNITY] {opp['pair']}: {opp['spread']:.2f}% spread")

    def log_error(self, error: str):
        """Log error"""
        print(f"[ERROR] {error}")
