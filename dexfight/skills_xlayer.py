"""
OKX Onchain OS integration for FlashArb.

This module now contains a real API client for the official OKX Onchain OS
DEX endpoints instead of returning simulated placeholders.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

import requests

API_BASE_URL = os.getenv("ONCHAINOS_API_BASE", "https://web3.okx.com").rstrip("/")
DEFAULT_CHAIN_INDEX = os.getenv("ONCHAINOS_CHAIN_INDEX", os.getenv("CHAIN_ID", "196"))
NATIVE_TOKEN_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

DEX_NAME_ALIASES = {
    "uniswap-v2": ("uniswap v2",),
    "uniswap-v3": ("uniswap v3",),
    "uniswap-v4": ("uniswap v4",),
    "quickswap-v3": ("quickswap v3",),
    "revoswap-v2": ("revoswap v2",),
    "revoswap-v3": ("revoswap v3",),
    "curve": ("curveng", "curve ng"),
    "xlayer-swap": ("x layer swap",),
    "okie-stable": ("okiestableswap", "okie stable"),
    "okie-v2": ("okieswap v2",),
    "okie-v3": ("okieswap v3",),
}


def normalize_token_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper().replace("₮", "T"))

# Public-facing summary of relevant Onchain OS skills.
OKX_SKILLS = {
    "okx-agentic-wallet": {
        "description": "Wallet lifecycle and signing",
        "actions": ["authorize", "balance", "send", "history"],
    },
    "okx-wallet-portfolio": {
        "description": "Portfolio balances and valuation",
        "actions": ["balance", "holdings", "value"],
    },
    "okx-dex-market": {
        "description": "DEX market data and quotes",
        "actions": ["price", "chart", "pnl", "liquidity"],
    },
    "okx-dex-swap": {
        "description": "DEX aggregator quote and swap execution",
        "actions": ["quote", "swap", "approve"],
    },
    "okx-dex-token": {
        "description": "Token discovery and metadata",
        "actions": ["search", "metadata", "list"],
    },
    "okx-security": {
        "description": "Risk checks and transaction simulation",
        "actions": ["token_risk", "phishing", "simulate", "sign"],
    },
    "okx-onchain-gateway": {
        "description": "Gas estimation and transaction tracking",
        "actions": ["gas", "simulate", "broadcast", "track"],
    },
}

DEXFIGHT_SKILLS = [
    "okx-agentic-wallet",
    "okx-wallet-portfolio",
    "okx-dex-market",
    "okx-dex-swap",
    "okx-dex-token",
    "okx-security",
    "okx-onchain-gateway",
]


@dataclass
class TokenInfo:
    symbol: str
    address: str
    decimals: int
    name: str = ""
    logo_url: str = ""


class OnchainOSAPIError(RuntimeError):
    """Raised when the OKX Onchain OS API returns an error."""


class OKXSkillRunner:
    """Thin client for the official OKX Onchain OS REST API."""

    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.api_key = api_key or os.getenv("ONCHAINOS_API_KEY", "") or os.getenv("OKX_API_KEY", "")
        self.api_secret = api_secret or os.getenv("ONCHAINOS_API_SECRET", "") or os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = passphrase or os.getenv("ONCHAINOS_API_PASSPHRASE", "") or os.getenv("OKX_PASSPHRASE", "")
        self.base_url = API_BASE_URL
        self.wallet_address = os.getenv("WALLET_ADDRESS", "")
        self.chain_index = DEFAULT_CHAIN_INDEX
        self.timeout = int(os.getenv("ONCHAINOS_TIMEOUT", "20"))
        self.proxy = (
            os.getenv("ONCHAINOS_PROXY", "").strip()
            or os.getenv("OKX_AGENT_PROXY", "").strip()
            or os.getenv("HTTPS_PROXY", "").strip()
        )
        self.session = requests.Session()
        if self.proxy:
            self.session.proxies.update({"http": self.proxy, "https": self.proxy})
        self._token_cache: Dict[str, TokenInfo] = {}
        self._liquidity_cache: Optional[List[Dict[str, str]]] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.passphrase)

    def _timestamp(self) -> str:
        now = datetime.now(timezone.utc)
        return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        digest = hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def _headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        if not self.is_configured:
            raise OnchainOSAPIError(
                "Missing ONCHAINOS_API_KEY / ONCHAINOS_API_SECRET / ONCHAINOS_API_PASSPHRASE"
            )
        timestamp = self._timestamp()
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "User-Agent": "flasharb-onchainos-client/1.0",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        method = method.upper()
        query = urlencode(params, doseq=True)
        request_path = path if not query else f"{path}?{query}"
        body = json.dumps(json_body, separators=(",", ":")) if json_body else ""
        headers = self._headers(method, request_path, body)
        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            params=params or None,
            json=json_body,
            headers=headers,
            timeout=self.timeout,
        )
        payload = response.json() if "application/json" in response.headers.get("content-type", "") else {"raw": response.text}
        if response.status_code >= 400:
            raise OnchainOSAPIError(f"HTTP {response.status_code}: {payload}")
        if isinstance(payload, dict) and payload.get("code") not in (None, "0", 0):
            raise OnchainOSAPIError(f"OKX API error {payload.get('code')}: {payload.get('msg') or payload}")
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    @staticmethod
    def to_base_units(amount: Decimal | float | str, decimals: int) -> str:
        quantized = Decimal(str(amount)) * (Decimal(10) ** decimals)
        return str(int(quantized.to_integral_value(rounding=ROUND_DOWN)))

    @staticmethod
    def from_base_units(amount: str | int, decimals: int) -> Decimal:
        return Decimal(str(amount)) / (Decimal(10) ** decimals)

    def get_supported_tokens(self, chain_index: Optional[str] = None, *, refresh: bool = False) -> List[TokenInfo]:
        if self._token_cache and not refresh:
            return list({id(token): token for token in self._token_cache.values()}.values())
        data = self._request(
            "GET",
            "/api/v6/dex/aggregator/all-tokens",
            params={"chainIndex": chain_index or self.chain_index},
        )
        tokens: Dict[str, TokenInfo] = {}
        for raw in data:
            symbol = str(raw.get("tokenSymbol", "")).upper()
            address = raw.get("tokenContractAddress", "")
            if not symbol or not address:
                continue
            token = TokenInfo(
                symbol=symbol,
                address=address,
                decimals=int(raw.get("decimals", 18)),
                name=raw.get("tokenName", ""),
                logo_url=raw.get("tokenLogoUrl", ""),
            )
            tokens[symbol] = token
            tokens[normalize_token_symbol(symbol)] = token
        self._token_cache = tokens
        return list({id(token): token for token in tokens.values()}.values())

    def resolve_token(self, symbol_or_address: str, chain_index: Optional[str] = None) -> TokenInfo:
        if symbol_or_address.lower() == NATIVE_TOKEN_ADDRESS:
            return TokenInfo(symbol="NATIVE", address=NATIVE_TOKEN_ADDRESS, decimals=18, name="Native")
        if symbol_or_address.startswith("0x") and len(symbol_or_address) == 42:
            tokens = self.get_supported_tokens(chain_index)
            for token in tokens:
                if token.address.lower() == symbol_or_address.lower():
                    return token
            return TokenInfo(symbol=symbol_or_address[-4:].upper(), address=symbol_or_address, decimals=18)

        symbol = symbol_or_address.upper()
        normalized = normalize_token_symbol(symbol)
        tokens = self.get_supported_tokens(chain_index)
        if symbol in self._token_cache:
            return self._token_cache[symbol]
        if normalized in self._token_cache:
            return self._token_cache[normalized]
        matches = [token for token in tokens if normalize_token_symbol(token.symbol) == normalized]
        if not matches:
            raise OnchainOSAPIError(f"Token not found on chain {chain_index or self.chain_index}: {symbol_or_address}")
        return matches[0]

    def get_liquidity_sources(self, chain_index: Optional[str] = None, *, refresh: bool = False) -> List[Dict[str, str]]:
        if self._liquidity_cache is not None and not refresh:
            return self._liquidity_cache
        data = self._request(
            "GET",
            "/api/v6/dex/aggregator/get-liquidity",
            params={"chainIndex": chain_index or self.chain_index},
        )
        self._liquidity_cache = [{"id": str(item.get("id", "")), "name": item.get("name", "")} for item in data]
        return self._liquidity_cache

    def get_liquidity_id_map(self, names: Iterable[str], chain_index: Optional[str] = None) -> Dict[str, str]:
        desired = {name.lower(): name for name in names}
        sources = self.get_liquidity_sources(chain_index)
        normalized_sources = {item["name"].lower(): item for item in sources}
        resolved: Dict[str, str] = {}
        for key, original in desired.items():
            if key.isdigit():
                resolved[original] = key
                continue
            alias_patterns = DEX_NAME_ALIASES.get(key, (key,))
            for pattern in alias_patterns:
                exact_match = normalized_sources.get(pattern)
                if exact_match:
                    resolved[original] = exact_match["id"]
                    break
            if original in resolved:
                continue
            for item in sources:
                normalized = item["name"].lower()
                if any(pattern in normalized or normalized in pattern for pattern in alias_patterns):
                    resolved[original] = item["id"]
                    break
        return resolved

    def quote(
        self,
        *,
        amount: str,
        from_token_address: str,
        to_token_address: str,
        chain_index: Optional[str] = None,
        swap_mode: str = "exactIn",
        dex_ids: Optional[str] = None,
        single_route_only: bool = True,
        single_pool_per_hop: bool = True,
        price_impact_protection_percent: str = "15",
    ) -> Dict[str, Any]:
        data = self._request(
            "GET",
            "/api/v6/dex/aggregator/quote",
            params={
                "chainIndex": chain_index or self.chain_index,
                "amount": amount,
                "swapMode": swap_mode,
                "fromTokenAddress": from_token_address,
                "toTokenAddress": to_token_address,
                "dexIds": dex_ids,
                "singleRouteOnly": str(single_route_only).lower(),
                "singlePoolPerHop": str(single_pool_per_hop).lower(),
                "priceImpactProtectionPercent": price_impact_protection_percent,
            },
        )
        if not data:
            raise OnchainOSAPIError("Empty quote response")
        return data[0]

    def approve_transaction(
        self,
        *,
        token_contract_address: str,
        approve_amount: str,
        chain_index: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = self._request(
            "GET",
            "/api/v6/dex/aggregator/approve-transaction",
            params={
                "chainIndex": chain_index or self.chain_index,
                "tokenContractAddress": token_contract_address,
                "approveAmount": approve_amount,
            },
        )
        if not data:
            raise OnchainOSAPIError("Empty approve response")
        return data[0]

    def swap(
        self,
        *,
        amount: str,
        from_token_address: str,
        to_token_address: str,
        user_wallet_address: str,
        slippage_percent: str,
        chain_index: Optional[str] = None,
        dex_ids: Optional[str] = None,
        approve_amount: Optional[str] = None,
        approve_transaction: bool = False,
        single_route_only: bool = True,
        single_pool_per_hop: bool = True,
        price_impact_protection_percent: str = "15",
        gas_level: str = "fast",
    ) -> Dict[str, Any]:
        data = self._request(
            "GET",
            "/api/v6/dex/aggregator/swap",
            params={
                "chainIndex": chain_index or self.chain_index,
                "amount": amount,
                "swapMode": "exactIn",
                "fromTokenAddress": from_token_address,
                "toTokenAddress": to_token_address,
                "slippagePercent": slippage_percent,
                "userWalletAddress": user_wallet_address,
                "approveAmount": approve_amount,
                "approveTransaction": str(approve_transaction).lower() if approve_transaction else None,
                "dexIds": dex_ids,
                "singleRouteOnly": str(single_route_only).lower(),
                "singlePoolPerHop": str(single_pool_per_hop).lower(),
                "priceImpactProtectionPercent": price_impact_protection_percent,
                "gasLevel": gas_level,
            },
        )
        if not data:
            raise OnchainOSAPIError("Empty swap response")
        return data[0]

    def run_skill(self, skill: str, action: str, **params: Any) -> Dict[str, Any]:
        """Compatibility shim for existing codepaths."""
        skill = skill.strip()
        action = action.strip()

        if skill == "okx-dex-token" and action in {"search", "metadata", "list"}:
            query = params.get("query") or params.get("symbol")
            if query:
                token = self.resolve_token(str(query), params.get("chain_index"))
                return {"skill": skill, "action": action, "status": "success", "data": token.__dict__}
            tokens = [token.__dict__ for token in self.get_supported_tokens(params.get("chain_index"))]
            return {"skill": skill, "action": action, "status": "success", "data": tokens}

        if skill == "okx-dex-swap" and action == "quote":
            result = self.quote(
                amount=str(params["amount"]),
                from_token_address=params["from_token_address"],
                to_token_address=params["to_token_address"],
                chain_index=params.get("chain_index"),
                dex_ids=params.get("dex_ids"),
                single_route_only=params.get("single_route_only", True),
                single_pool_per_hop=params.get("single_pool_per_hop", True),
                price_impact_protection_percent=str(params.get("price_impact_protection_percent", "15")),
            )
            return {"skill": skill, "action": action, "status": "success", "data": result}

        if skill == "okx-dex-swap" and action == "approve":
            result = self.approve_transaction(
                token_contract_address=params["token_contract_address"],
                approve_amount=str(params["approve_amount"]),
                chain_index=params.get("chain_index"),
            )
            return {"skill": skill, "action": action, "status": "success", "data": result}

        if skill == "okx-dex-swap" and action == "swap":
            result = self.swap(
                amount=str(params["amount"]),
                from_token_address=params["from_token_address"],
                to_token_address=params["to_token_address"],
                user_wallet_address=params.get("user_wallet_address") or self.wallet_address,
                slippage_percent=str(params.get("slippage_percent", "0.5")),
                chain_index=params.get("chain_index"),
                dex_ids=params.get("dex_ids"),
                approve_amount=params.get("approve_amount"),
                approve_transaction=params.get("approve_transaction", False),
                single_route_only=params.get("single_route_only", True),
                single_pool_per_hop=params.get("single_pool_per_hop", True),
                price_impact_protection_percent=str(params.get("price_impact_protection_percent", "15")),
                gas_level=params.get("gas_level", "fast"),
            )
            return {"skill": skill, "action": action, "status": "success", "data": result}

        if skill == "okx-dex-market" and action in {"price", "pnl", "liquidity"}:
            result = self.quote(
                amount=str(params["amount"]),
                from_token_address=params["from_token_address"],
                to_token_address=params["to_token_address"],
                chain_index=params.get("chain_index"),
                dex_ids=params.get("dex_ids"),
                single_route_only=params.get("single_route_only", True),
                single_pool_per_hop=params.get("single_pool_per_hop", True),
                price_impact_protection_percent=str(params.get("price_impact_protection_percent", "15")),
            )
            return {"skill": skill, "action": action, "status": "success", "data": result}

        if skill == "okx-wallet-portfolio" and action in {"balance", "holdings", "value"}:
            return {
                "skill": skill,
                "action": action,
                "status": "unsupported",
                "message": "Portfolio endpoints are not wired in this lightweight client yet.",
            }

        raise OnchainOSAPIError(f"Unsupported skill/action: {skill}.{action}")


def get_skills_usage() -> Dict[str, Any]:
    return {
        "total_available": len(OKX_SKILLS),
        "used_by_us": len(DEXFIGHT_SKILLS),
        "skills": DEXFIGHT_SKILLS,
        "api_base": API_BASE_URL,
        "chain_index": DEFAULT_CHAIN_INDEX,
    }


if __name__ == "__main__":
    print(json.dumps(get_skills_usage(), indent=2))
