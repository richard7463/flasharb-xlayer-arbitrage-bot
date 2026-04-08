"""
Telegram Notifications
Send alerts for trades and opportunities
"""

import requests
from typing import Dict, Optional


class TelegramNotifier:
    """Telegram bot notifications"""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        if not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            resp = requests.post(url, json=data, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def notify_opportunity(self, opp: Dict):
        """Notify about arbitrage opportunity"""
        text = f"🔍 *Arbitrage Opportunity*\n\n"
        text += f"Pair: `{opp['pair']}`\n"
        text += f"Spread: `{opp['spread']:.2f}%`\n"
        text += f"Buy: {opp['buy_dex']}\n"
        text += f"Sell: {opp['sell_dex']}"

        self.send_message(text)

    def notify_trade(self, trade: Dict):
        """Notify about executed trade"""
        text = f"✅ *Trade Executed*\n\n"
        text += f"Pair: `{trade.get('pair', 'N/A')}`\n"
        text += f"Status: {trade.get('status', 'success')}\n"

        if trade.get("profit"):
            text += f"Profit: `{trade['profit']:.4f}`"

        self.send_message(text)

    def notify_error(self, error: str):
        """Notify about error"""
        text = f"⚠️ *Error*\n\n{error}"
        self.send_message(text)
