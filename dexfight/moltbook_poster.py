"""
MOLTBOOK Automatic Poster
========================
Agent 自动发帖到 MOLTBOOK (real API mode)
"""

from __future__ import annotations

import os
import re
from difflib import get_close_matches
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests


class MOLTBOOKPoster:
    """自动发帖到 MOLTBOOK"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("MOLTBOOK_API_KEY", "")
        self.base_url = os.getenv("MOLTBOOK_API_BASE", "https://www.moltbook.com/api/v1").rstrip("/")
        self.submolt = os.getenv("MOLTBOOK_SUBMOLT", "buildx")
        self.timeout = int(os.getenv("MOLTBOOK_TIMEOUT", "20"))
        self.mock_mode = os.getenv("MOLTBOOK_MOCK_MODE", "false").lower() == "true"
        self.proxies = self._build_proxies()

    def _build_proxies(self) -> Optional[Dict[str, str]]:
        proxy = os.getenv("MOLTBOOK_PROXY", "").strip()
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "flasharb-moltbook-poster/1.0",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            timeout=self.timeout,
            proxies=self.proxies,
            **kwargs,
        )

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9\s]", " ", text.lower())

    def _parse_number_words(self, tokens: List[str], start: int) -> Tuple[Optional[float], int]:
        units = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19,
        }
        tens = {
            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        }
        multipliers = {"hundred": 100, "thousand": 1000}
        number_words = set(units) | set(tens) | set(multipliers) | {"and"}
        non_number_stops = {
            "the", "for", "and", "with", "from", "that", "this", "what", "when", "where",
            "has", "have", "had", "its", "his", "her", "new", "now", "how", "who", "why",
        }

        words_list = list(number_words)

        def fuzzy(word: str, cutoff: float) -> Optional[str]:
            match = get_close_matches(word, words_list, n=1, cutoff=cutoff)
            return match[0] if match else None

        def canon(word: str) -> str:
            if word in number_words:
                return word
            if len(word) < 4 or word in non_number_stops:
                return word
            match = fuzzy(word, 0.86)
            return match if match else word

        def canon_from_span(idx: int) -> Tuple[str, int]:
            direct = canon(tokens[idx])
            if direct in number_words:
                return direct, 1
            for span in (3, 2):
                if idx + span <= len(tokens):
                    merged = "".join(tokens[idx:idx + span])
                    merged_canon = merged
                    if len(merged) >= 4:
                        merged_hit = fuzzy(merged, 0.72)
                        if merged_hit:
                            merged_canon = merged_hit
                    if merged_canon in number_words:
                        return merged_canon, span
            return direct, 1

        i = start
        current = 0
        total = 0
        seen = False

        while i < len(tokens):
            t, span = canon_from_span(i)
            if t not in number_words:
                break
            if t == "and":
                i += span
                continue
            seen = True
            if t in units:
                current += units[t]
            elif t in tens:
                current += tens[t]
            elif t == "hundred":
                current = max(1, current) * 100
            elif t == "thousand":
                total += max(1, current) * 1000
                current = 0
            i += span

        if not seen:
            return None, 0
        return float(total + current), i - start

    def _extract_numbers(self, challenge: str) -> List[float]:
        nums: List[float] = []
        for m in re.findall(r"-?\d+(?:\.\d+)?", challenge):
            try:
                nums.append(float(m))
            except ValueError:
                pass

        normalized = self._normalize_text(challenge)
        tokens = [t for t in normalized.split() if t]
        i = 0
        while i < len(tokens):
            value, consumed = self._parse_number_words(tokens, i)
            if consumed > 0 and value is not None:
                nums.append(value)
                i += consumed
            else:
                i += 1
        return nums

    def _detect_operation(self, challenge: str) -> Optional[str]:
        txt = self._normalize_text(challenge)
        if any(k in txt for k in ["total", "sum", "combined", "together"]):
            return "+"
        if any(k in txt for k in ["slows by", "decrease by", "decreases by", "minus", "subtract", "less by"]):
            return "-"
        if any(k in txt for k in ["speeds up by", "increase by", "increases by", "plus", "add", "gains"]):
            return "+"
        if any(k in txt for k in ["multiplied by", "times by", "times"]):
            return "*"
        if any(k in txt for k in ["divided by", "divide by"]):
            return "/"
        symbols = re.findall(r"[+\-*/]", challenge)
        if symbols:
            return symbols[0]
        return None

    def _solve_challenge(self, challenge: str) -> Dict[str, Any]:
        numbers = self._extract_numbers(challenge)
        op = self._detect_operation(challenge)
        if len(numbers) < 2 or op is None:
            return {"success": False, "error": "unable to parse challenge", "challenge": challenge, "numbers": numbers, "op": op}

        a, b = numbers[0], numbers[1]
        if op == "+":
            val = a + b
        elif op == "-":
            val = a - b
        elif op == "*":
            val = a * b
        elif op == "/":
            if b == 0:
                return {"success": False, "error": "division by zero"}
            val = a / b
        else:
            return {"success": False, "error": f"unsupported op: {op}"}

        answer = f"{val:.2f}"
        return {"success": True, "answer": answer, "numbers": [a, b], "op": op}

    def _auto_verify_if_needed(self, post_response: Dict[str, Any]) -> Dict[str, Any]:
        post = post_response.get("post", {})
        verification = post.get("verification")
        if not verification:
            return {"success": True, "verified": False, "reason": "no_verification_required"}

        verification_code = verification.get("verification_code")
        challenge_text = verification.get("challenge_text", "")
        if not verification_code or not challenge_text:
            return {"success": False, "verified": False, "error": "missing verification fields", "verification": verification}

        solved = self._solve_challenge(challenge_text)
        if not solved.get("success"):
            return {"success": False, "verified": False, "error": "solve failed", "solve": solved}

        payload = {"verification_code": verification_code, "answer": solved["answer"]}
        try:
            resp = self._request("POST", "/verify", headers=self._headers(), json=payload)
            body = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
            if resp.status_code not in (200, 201):
                return {"success": False, "verified": False, "status_code": resp.status_code, "response": body, "solve": solved}
            return {"success": True, "verified": True, "response": body, "solve": solved}
        except Exception as exc:
            return {"success": False, "verified": False, "error": str(exc), "solve": solved}

    def check_claim_status(self) -> Dict[str, Any]:
        """检查 agent 是否已被 owner claim"""
        if not self.api_key:
            return {"success": False, "error": "MOLTBOOK_API_KEY not set"}

        try:
            resp = self._request("GET", "/agents/status", headers=self._headers())
            body = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code, "response": body}
            return {"success": True, "status": body.get("status", "unknown"), "response": body}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _create_post(self, title: str, content: str, submolt_name: Optional[str] = None) -> Dict[str, Any]:
        if self.mock_mode:
            print("📱 MOLTBOOK Post (mock):")
            print(title)
            print(content)
            return {"success": True, "mock": True, "title": title}

        if not self.api_key:
            return {"success": False, "error": "MOLTBOOK_API_KEY not set"}

        claim = self.check_claim_status()
        if not claim.get("success"):
            return {"success": False, "error": "claim status check failed", "claim": claim}
        if claim.get("status") != "claimed":
            return {"success": False, "error": f"agent not claimed yet: {claim.get('status')}", "claim": claim}

        payload = {
            "submolt_name": submolt_name or self.submolt,
            "title": title[:300],
            "content": content[:40000],
            "type": "text",
        }

        try:
            resp = self._request("POST", "/posts", headers=self._headers(), json=payload)
            body = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
            if resp.status_code not in (200, 201):
                return {"success": False, "status_code": resp.status_code, "response": body}
            verify_result = self._auto_verify_if_needed(body if isinstance(body, dict) else {})
            return {"success": True, "status_code": resp.status_code, "response": body, "verification": verify_result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def post_update(self, stats: dict, status: str = "running") -> dict:
        """
        自动发交易更新

        Args:
            stats: {"total_trades": 10, "profit": 0.5, ...}
            status: running/stopped
        """
        title = f"DexFight X Layer Update | trades={stats.get('total_trades', 0)} | status={status}"
        content = self._format_update(stats, status)
        return self._create_post(title=title, content=content)

    def submit_project(self, repo_url: str, wallet: str = "") -> dict:
        """
        发项目提交帖

        Args:
            repo_url: GitHub repo URL
            wallet: 钱包地址
        """
        title = "ProjectSubmission XLayerArena - DexFight X Layer Arbitrage Bot"
        content = self._format_submission(repo_url, wallet)
        return self._create_post(title=title, content=content)

    def _format_update(self, stats: dict, status: str) -> str:
        """格式化更新内容"""
        return f"""
## DexFight X Layer - Live Update

**Wallet:** `{stats.get('wallet', 'N/A')}`
**Total Trades:** {stats.get('total_trades', 0)}
**Total Profit:** ${stats.get('total_profit', 0):.4f}
**Average Profit/Trade:** ${stats.get('avg_profit', 0):.4f}

### Recent Transactions
```text
{stats.get('recent', 'No recent trades')}
```

### On-Chain Activity

- Network: X Layer (Chain ID: 196)
- Status: {status}

_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
""".strip()

    def _format_submission(self, repo_url: str, wallet: str) -> str:
        """格式化项目提交"""
        return f"""
## ProjectSubmission XLayerArena - DexFight X Layer Arbitrage Bot

**Forked from:** dexfight
**Adapted for:** X Layer

### Features
- Multi-DEX: Uniswap V3, Sushiswap, Pancakeswap, OKX
- Price impact calculation
- Smart execution with gap filtering
- Mock mode for testing

### OKX Skills
- okx-dex-market
- okx-dex-swap
- okx-security
- okx-wallet-portfolio

### Status
Live on X Layer

**GitHub:** {repo_url}
**Wallet:** {wallet or "N/A"}
""".strip()


# ============== 集成到 run.py ==============
def add_moltbook_posting(bot, post_interval: int = 300):
    """
    添加自动发帖到 bot

    Args:
        bot: ArbitrageBot 实例
        post_interval: 发帖间隔 (秒)
    """
    poster = MOLTBOOKPoster()

    # 启动时发帖
    result = poster.submit_project(
        repo_url="https://github.com/YOUR_USERNAME/xlayer-arbitrage-bot",
        wallet=bot.config.get("WALLET_ADDRESS", "")
    )
    print(f"📱 MOLTBOOK submit result: {result}")

    # 定期发帖
    # 每个 post_interval sec 发一次
    print(f"📱 MOLTBOOK auto-posting every {post_interval}s")


if __name__ == "__main__":
    # 测试发帖
    poster = MOLTBOOKPoster()

    print("Claim status:", poster.check_claim_status())

    # 测试项目提交
    print(poster.submit_project(
        repo_url="https://github.com/YOUR_USERNAME/xlayer-arbitrage-bot",
        wallet="0x..."
    ))

    # 测试交易更新
    print(poster.post_update({
        "total_trades": 100,
        "total_profit": 1.5,
        "avg_profit": 0.015,
        "wallet": "0x...",
        "recent": "#99: 0.5% spread, $0.01 profit\n#100: 0.8% spread, $0.02 profit"
    }))
