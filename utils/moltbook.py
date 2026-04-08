"""
Moltbook Posting
Post trade activities to Moltbook
"""

import requests
from typing import Dict, Optional


class MoltbookPoster:
    """Post activities to Moltbook"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def post_activity(self, content: str, metadata: Optional[Dict] = None) -> bool:
        """Post activity to Moltbook"""
        if not self.api_key:
            return False

        url = "https://api.moltbook.com/v1/activities"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "content": content,
            "type": "arbitrage_bot"
        }

        if metadata:
            data["metadata"] = metadata

        try:
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return resp.status_code in (200, 201)
        except Exception:
            return False

    def post_trade(self, trade: Dict):
        """Post trade execution"""
        content = f"🤖 Arbitrage Bot executed trade: {trade.get('pair', 'N/A')}"
        metadata = {
            "spread": trade.get("spread"),
            "buy_dex": trade.get("buy_dex"),
            "sell_dex": trade.get("sell_dex"),
            "status": trade.get("status")
        }

        self.post_activity(content, metadata)

    def post_opportunity(self, opp: Dict):
        """Post found opportunity"""
        content = f"🔍 Found arbitrage: {opp['pair']} - {opp['spread']:.2f}% spread"
        metadata = {
            "buy_dex": opp["buy_dex"],
            "sell_dex": opp["sell_dex"]
        }

        self.post_activity(content, metadata)
