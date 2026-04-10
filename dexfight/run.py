#!/usr/bin/env python3
"""FlashArb runtime.

This replaces the old random-price demo loop with a real OKX Onchain OS-powered
scanner. In paper mode it scans live quotes and reports opportunities. In live
mode it also sends approval + swap transactions and posts status updates to
Moltbook when configured.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from eth_account import Account
except ModuleNotFoundError:  # pragma: no cover - optional in agentic mode
    Account = None  # type: ignore[assignment]

try:
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - optional in agentic mode
    Web3 = None  # type: ignore[assignment]

from moltbook_poster import MOLTBOOKPoster
from skills_xlayer import OKXSkillRunner, OnchainOSAPIError, TokenInfo

ERC20_BALANCE_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class FlashArbConfig:
    mode: str = "paper"
    chain_id: int = 196
    chain_index: str = "196"
    rpc_url: str = "https://rpc.xlayer.com"
    base_token: str = "auto"
    base_token_candidates: List[str] = field(default_factory=lambda: ["USDT0", "USDC", "USDT"])
    target_tokens: List[str] = field(default_factory=lambda: ["OKB", "USDC", "WBTC"])
    dex_names: List[str] = field(default_factory=lambda: ["uniswap", "quickswap", "revoswap", "okie"])
    trade_amount: Decimal = Decimal("5")
    min_profit_usd: Decimal = Decimal("0.05")
    min_spread_pct: Decimal = Decimal("0.30")
    max_price_impact_pct: Decimal = Decimal("2.00")
    slippage_percent: str = "0.50"
    check_interval: int = 45
    post_interval: int = 180
    max_trades_per_hour: int = 10
    max_daily_loss_usd: Decimal = Decimal("20")
    idle_probe_enabled: bool = False
    idle_probe_amount_usd: Decimal = Decimal("0.30")
    idle_probe_interval: int = 900
    idle_probe_token: str = "OKB"
    rate_limit_cooldown_sec: int = 180
    agentic_order_retry_count: int = 5
    agentic_order_retry_delay_sec: int = 8
    single_route_only: bool = True
    single_pool_per_hop: bool = True
    gas_limit_multiplier: Decimal = Decimal("1.30")
    approve_gas_limit: int = 120000
    log_dir: Path = Path("logs")
    repo_url: str = os.getenv("FLASHARB_REPO_URL", "")
    wallet_address: str = os.getenv("WALLET_ADDRESS", "")
    private_key: str = os.getenv("PRIVATE_KEY", "")
    execution_backend: str = os.getenv("FLASHARB_EXECUTION_BACKEND", "auto")

    @classmethod
    def from_env(cls, live: bool = False) -> "FlashArbConfig":
        tokens = [item.strip() for item in os.getenv("FLASHARB_TOKENS", "OKB,USDC,WBTC").split(",") if item.strip()]
        dexes = [item.strip() for item in os.getenv("FLASHARB_DEXES", "uniswap,quickswap,revoswap,okie").split(",") if item.strip()]
        base_candidates = [
            item.strip() for item in os.getenv("FLASHARB_BASE_TOKENS", os.getenv("FLASHARB_BASE_TOKEN", "USDT0,USDC,USDT")).split(",") if item.strip()
        ]
        return cls(
            mode="live" if live else os.getenv("FLASHARB_MODE", "paper"),
            chain_id=int(os.getenv("CHAIN_ID", "196")),
            chain_index=os.getenv("ONCHAINOS_CHAIN_INDEX", "196"),
            rpc_url=os.getenv("RPC_URL", "https://rpc.xlayer.com"),
            base_token=os.getenv("FLASHARB_BASE_TOKEN", "auto"),
            base_token_candidates=base_candidates,
            target_tokens=tokens,
            dex_names=dexes,
            trade_amount=Decimal(os.getenv("TRADE_AMOUNT_USD", os.getenv("TRADE_AMOUNT", "5"))),
            min_profit_usd=Decimal(os.getenv("FLASHARB_MIN_PROFIT_USD", "0.05")),
            min_spread_pct=Decimal(os.getenv("FLASHARB_MIN_SPREAD_PCT", "0.30")),
            max_price_impact_pct=Decimal(os.getenv("FLASHARB_MAX_PRICE_IMPACT_PCT", "2.00")),
            slippage_percent=os.getenv("FLASHARB_SLIPPAGE_PERCENT", "0.50"),
            check_interval=int(os.getenv("CHECK_INTERVAL", "45")),
            post_interval=int(os.getenv("MOLTBOOK_POST_INTERVAL", "600")),
            max_trades_per_hour=int(os.getenv("FLASHARB_MAX_TRADES_PER_HOUR", "10")),
            max_daily_loss_usd=Decimal(os.getenv("FLASHARB_MAX_DAILY_LOSS_USD", "20")),
            idle_probe_enabled=os.getenv("FLASHARB_IDLE_PROBE_ENABLED", "false").lower() == "true",
            idle_probe_amount_usd=Decimal(os.getenv("FLASHARB_IDLE_PROBE_AMOUNT_USD", "0.30")),
            idle_probe_interval=int(os.getenv("FLASHARB_IDLE_PROBE_INTERVAL", "900")),
            idle_probe_token=os.getenv("FLASHARB_IDLE_PROBE_TOKEN", "OKB"),
            rate_limit_cooldown_sec=int(os.getenv("FLASHARB_RATE_LIMIT_COOLDOWN_SEC", "180")),
            agentic_order_retry_count=int(os.getenv("FLASHARB_AGENTIC_ORDER_RETRY_COUNT", "5")),
            agentic_order_retry_delay_sec=int(os.getenv("FLASHARB_AGENTIC_ORDER_RETRY_DELAY_SEC", "8")),
            single_route_only=os.getenv("FLASHARB_SINGLE_ROUTE_ONLY", "true").lower() == "true",
            single_pool_per_hop=os.getenv("FLASHARB_SINGLE_POOL_PER_HOP", "true").lower() == "true",
            gas_limit_multiplier=Decimal(os.getenv("FLASHARB_GAS_LIMIT_MULTIPLIER", "1.30")),
            approve_gas_limit=int(os.getenv("FLASHARB_APPROVE_GAS_LIMIT", "120000")),
            log_dir=Path(os.getenv("FLASHARB_LOG_DIR", "logs")),
            repo_url=os.getenv("FLASHARB_REPO_URL", ""),
            wallet_address=os.getenv("WALLET_ADDRESS", ""),
            private_key=os.getenv("PRIVATE_KEY", ""),
            execution_backend=os.getenv("FLASHARB_EXECUTION_BACKEND", "auto"),
        )


class FlashArbBot:
    def __init__(self, config: FlashArbConfig):
        self.config = config
        self.client = OKXSkillRunner()
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url)) if Web3 else None
        self.poster = MOLTBOOKPoster() if os.getenv("MOLTBOOK_API_KEY") else None
        self.account = Account.from_key(config.private_key) if config.private_key and Account else None
        self.wallet_address = config.wallet_address or (self.account.address if self.account else "")
        self.execution_backend = self._detect_execution_backend()
        self.base_token: Optional[TokenInfo] = None
        self.target_tokens: List[TokenInfo] = []
        self.dex_map: Dict[str, str] = {}
        self.last_post_at = 0.0
        self.last_probe_at = 0.0
        self.rate_limited_until = 0.0
        self.recent_trade_times: List[float] = []
        self.event_log_path = config.log_dir / "flasharb_events.jsonl"
        self.state = {
            "start_time": time.time(),
            "cycles": 0,
            "total_trades": 0,
            "successful": 0,
            "failed": 0,
            "total_profit": Decimal("0"),
            "daily_realized_profit": Decimal("0"),
            "recent": [],
        }
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

    def _detect_execution_backend(self) -> str:
        requested = (self.config.execution_backend or "auto").strip().lower()
        if requested in {"private-key", "private_key"}:
            return "private-key"
        if requested == "agentic":
            return "agentic"
        return "private-key" if self.account else "agentic"

    def _cli_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"
        proxy = os.getenv("ONCHAINOS_PROXY", "").strip() or os.getenv("OKX_AGENT_PROXY", "").strip() or os.getenv("HTTPS_PROXY", "").strip()
        if proxy:
            env["HTTPS_PROXY"] = proxy
            env["HTTP_PROXY"] = proxy
        return env

    def _run_onchainos_cli(self, args: List[str]) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["onchainos", *args],
                check=True,
                capture_output=True,
                text=True,
                env=self._cli_env(),
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stdout or exc.stderr or "").strip()
            raise RuntimeError(f"onchainos {' '.join(args)} failed: {detail or exc}") from exc

    def _fetch_agentic_wallet_balances(self) -> Dict[str, Dict[str, Any]]:
        response = self._run_onchainos_cli(["wallet", "balance", "--force"])
        payload = response.get("data", {})
        if not self.wallet_address:
            self.wallet_address = payload.get("evmAddress", "") or self.wallet_address
        tokens = payload.get("details", [{}])[0].get("tokenAssets", [])
        balances: Dict[str, Dict[str, Any]] = {}
        for item in tokens:
            symbol = str(item.get("symbol") or item.get("customSymbol") or "").upper()
            if symbol:
                balances[symbol] = item
            token_address = str(item.get("tokenAddress") or "").lower()
            if token_address:
                balances[token_address] = item
        return balances

    def _select_base_token(self) -> TokenInfo:
        if self.config.base_token.lower() not in {"", "auto"}:
            return self.client.resolve_token(self.config.base_token, self.config.chain_index)
        candidates = self.config.base_token_candidates or ["USDT0", "USDC", "USDT"]
        if self.execution_backend == "agentic":
            balances = self._fetch_agentic_wallet_balances()
            best_token: Optional[TokenInfo] = None
            best_balance = Decimal("-1")
            for symbol in candidates:
                try:
                    token = self.client.resolve_token(symbol, self.config.chain_index)
                except Exception:
                    continue
                balance_item = balances.get(token.address.lower()) or balances.get(token.symbol.upper())
                if not balance_item:
                    continue
                balance = Decimal(str(balance_item.get("balance", "0")))
                if balance > best_balance:
                    best_token = token
                    best_balance = balance
            if best_token is not None:
                return best_token
        for symbol in candidates:
            try:
                return self.client.resolve_token(symbol, self.config.chain_index)
            except Exception:
                continue
        raise RuntimeError(f"Unable to resolve any base token from {candidates}")

    def initialize(self) -> None:
        if not self.client.is_configured:
            raise OnchainOSAPIError(
                "OnchainOS credentials are required. Set ONCHAINOS_API_KEY, ONCHAINOS_API_SECRET, ONCHAINOS_API_PASSPHRASE."
            )
        if self.config.mode == "live" and self.execution_backend == "private-key" and (not self.account or not self.wallet_address):
            raise RuntimeError("Live mode with private-key backend requires PRIVATE_KEY and WALLET_ADDRESS")
        if self.execution_backend == "private-key" and (not Web3 or not Account or self.w3 is None):
            raise RuntimeError("Private-key backend requires web3 and eth-account to be installed")
        if self.config.mode == "live" and self.execution_backend == "agentic":
            status = self._run_onchainos_cli(["wallet", "status"])
            if not status.get("data", {}).get("loggedIn"):
                raise RuntimeError("Live mode with agentic backend requires an authenticated Agentic Wallet session")
        self.base_token = self._select_base_token()
        resolved_targets: List[TokenInfo] = []
        for symbol in self.config.target_tokens:
            try:
                token = self.client.resolve_token(symbol, self.config.chain_index)
            except Exception as exc:
                self._record_event("target_token_skipped", {"symbol": symbol, "error": str(exc)})
                continue
            if token.address.lower() == self.base_token.address.lower():
                continue
            resolved_targets.append(token)
        self.target_tokens = resolved_targets
        if not self.target_tokens:
            raise RuntimeError(f"No valid target tokens resolved from {self.config.target_tokens}")
        self.dex_map = self.client.get_liquidity_id_map(self.config.dex_names, self.config.chain_index)
        if len(self.dex_map) < 2:
            raise RuntimeError(f"Not enough liquidity sources resolved from {self.config.dex_names}: {self.dex_map}")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _serialize(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, TokenInfo):
            return asdict(value)
        if isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._serialize(v) for v in value]
        return value

    def _record_event(self, kind: str, payload: Dict[str, Any]) -> None:
        event = {
            "timestamp": self._timestamp(),
            "kind": kind,
            "payload": self._serialize(payload),
        }
        with self.event_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")

    def _is_rate_limited_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "429" in message or "rate limit" in message or "too many requests" in message

    def _is_agentic_order_busy_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "another order processing" in message or "send-uop failed" in message

    def _trim_recent(self) -> None:
        cutoff = time.time() - 3600
        self.recent_trade_times = [ts for ts in self.recent_trade_times if ts >= cutoff]

    def _trade_allowed(self) -> bool:
        self._trim_recent()
        if len(self.recent_trade_times) >= self.config.max_trades_per_hour:
            return False
        if self.state["daily_realized_profit"] <= -self.config.max_daily_loss_usd:
            return False
        return True

    def _probe_allowed(self) -> bool:
        if not self.config.idle_probe_enabled or self.config.mode != "live":
            return False
        if not self._trade_allowed():
            return False
        if time.time() - self.last_probe_at < self.config.idle_probe_interval:
            return False
        return True

    def _balance_of(self, token: TokenInfo) -> int:
        if self.execution_backend == "agentic":
            balances = self._fetch_agentic_wallet_balances()
            item = balances.get(token.address.lower()) or balances.get(token.symbol.upper())
            if not item:
                return 0
            return int(self.client.to_base_units(Decimal(str(item.get("balance", "0"))), token.decimals))
        if self.w3 is None:
            raise RuntimeError("web3 is not available for private-key balance reads")
        if not self.wallet_address:
            return 0
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(token.address), abi=ERC20_BALANCE_ABI)
        return int(contract.functions.balanceOf(Web3.to_checksum_address(self.wallet_address)).call())

    def _allowance(self, token: TokenInfo, spender: str) -> int:
        if self.execution_backend == "agentic":
            return 0
        if self.w3 is None:
            raise RuntimeError("web3 is not available for private-key allowance reads")
        if not self.wallet_address:
            return 0
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(token.address), abi=ERC20_BALANCE_ABI)
        return int(
            contract.functions.allowance(
                Web3.to_checksum_address(self.wallet_address),
                Web3.to_checksum_address(spender),
            ).call()
        )

    def _sign_and_send_tx(self, tx: Dict[str, Any]) -> str:
        if not self.account:
            raise RuntimeError("No private key loaded")
        if self.w3 is None:
            raise RuntimeError("web3 is not available for private-key transaction sends")
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def _build_evm_tx(self, tx_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.wallet_address:
            raise RuntimeError("Wallet address missing")
        if self.w3 is None:
            raise RuntimeError("web3 is not available for private-key tx building")
        pending_block = self.w3.eth.get_block("pending")
        tx: Dict[str, Any] = {
            "chainId": self.config.chain_id,
            "from": Web3.to_checksum_address(self.wallet_address),
            "to": Web3.to_checksum_address(tx_payload["to"]),
            "data": tx_payload["data"],
            "value": int(tx_payload.get("value", "0")),
            "nonce": self.w3.eth.get_transaction_count(Web3.to_checksum_address(self.wallet_address)),
        }
        gas = tx_payload.get("gas")
        if gas:
            tx["gas"] = max(int(Decimal(str(gas)) * self.config.gas_limit_multiplier), 21000)
        if tx_payload.get("maxPriorityFeePerGas"):
            priority_fee = int(tx_payload["maxPriorityFeePerGas"])
            base_fee = int(pending_block.get("baseFeePerGas", tx_payload.get("gasPrice", priority_fee)))
            tx["maxPriorityFeePerGas"] = priority_fee
            tx["maxFeePerGas"] = tx_payload.get("maxFeePerGas")
            if tx["maxFeePerGas"] is None:
                tx["maxFeePerGas"] = base_fee * 2 + priority_fee
            else:
                tx["maxFeePerGas"] = int(tx["maxFeePerGas"])
        elif tx_payload.get("gasPrice"):
            tx["gasPrice"] = int(tx_payload["gasPrice"])
        return tx

    def _send_approval_if_needed(self, token: TokenInfo, approve_amount: str) -> Optional[str]:
        if self.execution_backend == "agentic":
            return None
        approve_info = self.client.approve_transaction(
            token_contract_address=token.address,
            approve_amount=approve_amount,
            chain_index=self.config.chain_index,
        )
        spender = approve_info["dexContractAddress"]
        current_allowance = self._allowance(token, spender)
        if current_allowance >= int(approve_amount):
            return None
        tx = {
            "chainId": self.config.chain_id,
            "from": Web3.to_checksum_address(self.wallet_address),
            "to": Web3.to_checksum_address(token.address),
            "data": approve_info["data"],
            "value": 0,
            "gas": self.config.approve_gas_limit,
            "nonce": self.w3.eth.get_transaction_count(Web3.to_checksum_address(self.wallet_address)),
        }
        gas_price = self.w3.eth.gas_price
        if gas_price:
            tx["gasPrice"] = int(gas_price)
        approve_hash = self._sign_and_send_tx(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError(f"Approval failed: {approve_hash}")
        return approve_hash

    def _agentic_execute_swap(self, from_token: TokenInfo, to_token: TokenInfo, *, readable_amount: Optional[Decimal] = None, raw_amount: Optional[str] = None) -> Dict[str, Any]:
        if not self.wallet_address:
            balances = self._fetch_agentic_wallet_balances()
            if not self.wallet_address:
                raise RuntimeError(f"Agentic wallet address unavailable: {balances}")
        args = [
            "swap",
            "execute",
            "--from",
            from_token.address,
            "--to",
            to_token.address,
            "--chain",
            "xlayer",
            "--wallet",
            self.wallet_address,
            "--slippage",
            self.config.slippage_percent,
        ]
        if raw_amount is not None:
            args.extend(["--amount", str(raw_amount)])
        elif readable_amount is not None:
            amount_str = format(readable_amount.normalize(), "f")
            args.extend(["--readable-amount", amount_str])
        else:
            raise RuntimeError("Swap execution requires readable_amount or raw_amount")
        last_error: Optional[Exception] = None
        for attempt in range(1, self.config.agentic_order_retry_count + 1):
            try:
                response = self._run_onchainos_cli(args)
                if not response.get("ok"):
                    raise RuntimeError(f"Agentic swap failed: {response}")
                return response["data"]
            except Exception as exc:
                last_error = exc
                if attempt >= self.config.agentic_order_retry_count or not self._is_agentic_order_busy_error(exc):
                    raise
                self._record_event(
                    "agentic_order_retry",
                    {
                        "attempt": attempt,
                        "max_attempts": self.config.agentic_order_retry_count,
                        "delay_sec": self.config.agentic_order_retry_delay_sec,
                        "from_token": from_token.symbol,
                        "to_token": to_token.symbol,
                        "error": str(exc),
                    },
                )
                time.sleep(self.config.agentic_order_retry_delay_sec)
        if last_error:
            raise last_error
        raise RuntimeError("Agentic swap failed without a specific error")

    def _quote(self, amount: str, from_token: TokenInfo, to_token: TokenInfo, dex_id: str) -> Dict[str, Any]:
        return self.client.quote(
            amount=amount,
            from_token_address=from_token.address,
            to_token_address=to_token.address,
            chain_index=self.config.chain_index,
            dex_ids=dex_id,
            single_route_only=self.config.single_route_only,
            single_pool_per_hop=self.config.single_pool_per_hop,
            price_impact_protection_percent=str(self.config.max_price_impact_pct),
        )

    def scan_best_opportunity(self) -> Optional[Dict[str, Any]]:
        assert self.base_token is not None
        best: Optional[Dict[str, Any]] = None
        base_amount = self.client.to_base_units(self.config.trade_amount, self.base_token.decimals)
        dex_items = list(self.dex_map.items())

        for token in self.target_tokens:
            for buy_name, buy_id in dex_items:
                try:
                    buy_quote = self._quote(base_amount, self.base_token, token, buy_id)
                except Exception as exc:
                    self._record_event("quote_error", {"token": token.symbol, "dex": buy_name, "side": "buy", "error": str(exc)})
                    if self._is_rate_limited_error(exc):
                        self.rate_limited_until = time.time() + self.config.rate_limit_cooldown_sec
                        self._record_event(
                            "quote_rate_limited",
                            {"cooldown_sec": self.config.rate_limit_cooldown_sec, "token": token.symbol, "dex": buy_name, "side": "buy"},
                        )
                        return None
                    continue

                buy_out = buy_quote.get("toTokenAmount")
                if not buy_out or int(buy_out) <= 0:
                    continue

                for sell_name, sell_id in dex_items:
                    if sell_id == buy_id:
                        continue
                    try:
                        sell_quote = self._quote(str(buy_out), token, self.base_token, sell_id)
                    except Exception as exc:
                        self._record_event("quote_error", {"token": token.symbol, "dex": sell_name, "side": "sell", "error": str(exc)})
                        if self._is_rate_limited_error(exc):
                            self.rate_limited_until = time.time() + self.config.rate_limit_cooldown_sec
                            self._record_event(
                                "quote_rate_limited",
                                {"cooldown_sec": self.config.rate_limit_cooldown_sec, "token": token.symbol, "dex": sell_name, "side": "sell"},
                            )
                            return None
                        continue

                    final_base = self.client.from_base_units(sell_quote["toTokenAmount"], self.base_token.decimals)
                    gross_profit = final_base - self.config.trade_amount
                    trade_fee = Decimal(str(buy_quote.get("tradeFee", "0"))) + Decimal(str(sell_quote.get("tradeFee", "0")))
                    estimated_profit = gross_profit - trade_fee
                    spread_pct = (estimated_profit / self.config.trade_amount) * Decimal("100")
                    max_impact = max(
                        abs(Decimal(str(buy_quote.get("priceImpactPercent", "0")))),
                        abs(Decimal(str(sell_quote.get("priceImpactPercent", "0")))),
                    )

                    if estimated_profit < self.config.min_profit_usd:
                        continue
                    if spread_pct < self.config.min_spread_pct:
                        continue
                    if max_impact > self.config.max_price_impact_pct:
                        continue

                    candidate = {
                        "token": token.symbol,
                        "buy_dex": buy_name,
                        "sell_dex": sell_name,
                        "buy_dex_id": buy_id,
                        "sell_dex_id": sell_id,
                        "input_usdc": str(self.config.trade_amount),
                        "expected_token_out": str(self.client.from_base_units(buy_out, token.decimals)),
                        "expected_usdc_back": str(final_base),
                        "trade_fee_usd": str(trade_fee),
                        "estimated_profit_usd": str(estimated_profit),
                        "estimated_spread_pct": str(spread_pct),
                        "max_price_impact_pct": str(max_impact),
                        "buy_quote": buy_quote,
                        "sell_quote": sell_quote,
                    }
                    if best is None or Decimal(best["estimated_profit_usd"]) < estimated_profit:
                        best = candidate
        return best

    def _broadcast_swap(self, swap_response: Dict[str, Any]) -> str:
        tx_payload = swap_response.get("tx")
        if not tx_payload:
            raise RuntimeError(f"Swap response missing tx payload: {swap_response}")
        tx = self._build_evm_tx(tx_payload)
        tx_hash = self._sign_and_send_tx(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1:
            raise RuntimeError(f"Swap failed: {tx_hash}")
        return tx_hash

    def _execute_roundtrip(
        self,
        token: TokenInfo,
        amount_readable: Decimal,
        *,
        label: str,
        buy_dex_id: Optional[str] = None,
        sell_dex_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert self.base_token is not None
        if not self._trade_allowed():
            return {"status": "skipped", "reason": "risk_limits", "profit_usd": "0", "label": label}

        base_before = self._balance_of(self.base_token)
        token_before = self._balance_of(token)
        amount_base_units = self.client.to_base_units(amount_readable, self.base_token.decimals)
        approval_hashes: List[str] = []

        if self.execution_backend == "agentic":
            buy_result = self._agentic_execute_swap(
                self.base_token,
                token,
                readable_amount=amount_readable,
            )
            buy_tx_hash = buy_result["swapTxHash"]
            if buy_result.get("approveTxHash"):
                approval_hashes.append(buy_result["approveTxHash"])
            received_token_amount = int(buy_result["toAmount"])
            if received_token_amount <= 0:
                raise RuntimeError("Buy leg confirmed but token output was zero")
            received_token_readable = self.client.from_base_units(received_token_amount, token.decimals)
            sell_result = self._agentic_execute_swap(
                token,
                self.base_token,
                readable_amount=received_token_readable,
            )
            sell_tx_hash = sell_result["swapTxHash"]
            if sell_result.get("approveTxHash"):
                approval_hashes.append(sell_result["approveTxHash"])
        else:
            approval_hash = self._send_approval_if_needed(self.base_token, amount_base_units)
            if approval_hash:
                approval_hashes.append(approval_hash)
            buy_swap = self.client.swap(
                amount=amount_base_units,
                from_token_address=self.base_token.address,
                to_token_address=token.address,
                user_wallet_address=self.wallet_address,
                slippage_percent=self.config.slippage_percent,
                chain_index=self.config.chain_index,
                dex_ids=buy_dex_id,
                approve_amount=amount_base_units,
                single_route_only=self.config.single_route_only,
                single_pool_per_hop=self.config.single_pool_per_hop,
                price_impact_protection_percent=str(self.config.max_price_impact_pct),
            )
            buy_tx_hash = self._broadcast_swap(buy_swap)
            token_after_buy = self._balance_of(token)
            received_token_amount = token_after_buy - token_before
            if received_token_amount <= 0:
                raise RuntimeError("Buy leg confirmed but token balance did not increase")
            second_approval_hash = self._send_approval_if_needed(token, str(received_token_amount))
            if second_approval_hash:
                approval_hashes.append(second_approval_hash)
            sell_swap = self.client.swap(
                amount=str(received_token_amount),
                from_token_address=token.address,
                to_token_address=self.base_token.address,
                user_wallet_address=self.wallet_address,
                slippage_percent=self.config.slippage_percent,
                chain_index=self.config.chain_index,
                dex_ids=sell_dex_id,
                approve_amount=str(received_token_amount),
                single_route_only=self.config.single_route_only,
                single_pool_per_hop=self.config.single_pool_per_hop,
                price_impact_protection_percent=str(self.config.max_price_impact_pct),
            )
            sell_tx_hash = self._broadcast_swap(sell_swap)

        base_after = self._balance_of(self.base_token)
        realized_profit = self.client.from_base_units(base_after - base_before, self.base_token.decimals)
        if label == "probe":
            self.last_probe_at = time.time()
        return {
            "status": "success" if label == "arb" else "probe",
            "profit_usd": str(realized_profit),
            "buy_tx_hash": buy_tx_hash,
            "sell_tx_hash": sell_tx_hash,
            "approval_hashes": approval_hashes,
            "backend": self.execution_backend,
            "label": label,
        }

    def execute(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        assert self.base_token is not None
        token = next(item for item in self.target_tokens if item.symbol == opportunity["token"])
        if self.config.mode != "live":
            return {
                "status": "paper",
                "profit_usd": opportunity["estimated_profit_usd"],
                "buy_tx_hash": None,
                "sell_tx_hash": None,
            }
        return self._execute_roundtrip(
            token,
            self.config.trade_amount,
            label="arb",
            buy_dex_id=opportunity["buy_dex_id"],
            sell_dex_id=opportunity["sell_dex_id"],
        )

    def _update_stats(self, opportunity: Optional[Dict[str, Any]], execution: Optional[Dict[str, Any]]) -> None:
        if not opportunity or not execution:
            return
        self.state["total_trades"] += 1
        profit = Decimal(str(execution.get("profit_usd", "0")))
        if execution.get("status") in {"success", "paper", "probe"}:
            self.state["successful"] += 1
            self.state["total_profit"] += profit
            self.state["daily_realized_profit"] += profit
            self.recent_trade_times.append(time.time())
        else:
            self.state["failed"] += 1
        recent_line = (
            f"{opportunity['token']} {opportunity['buy_dex']}->{opportunity['sell_dex']} "
            f"profit={profit} status={execution.get('status')} "
            f"buy={execution.get('buy_tx_hash')} sell={execution.get('sell_tx_hash')}"
        )
        self.state["recent"] = (self.state["recent"] + [recent_line])[-8:]

    def _maybe_post_update(self, force: bool = False) -> None:
        if not self.poster:
            return
        now = time.time()
        if not force and now - self.last_post_at < self.config.post_interval:
            return
        stats = {
            "wallet": self.wallet_address,
            "base_token": self.base_token.symbol if self.base_token else self.config.base_token,
            "cycles": self.state["cycles"],
            "total_trades": self.state["total_trades"],
            "total_profit": float(self.state["total_profit"]),
            "avg_profit": float(self.state["total_profit"] / max(1, self.state["successful"])),
            "recent": "\n".join(self.state["recent"][-5:]) or "No trades yet",
        }
        result = self.poster.post_update(stats, status=self.config.mode)
        self._record_event("moltbook_post", result)
        self.last_post_at = now

    def _run_probe_cycle(self, *, reason: str) -> Dict[str, Any]:
        probe_token = next((item for item in self.target_tokens if item.symbol == self.config.idle_probe_token), self.target_tokens[0])
        probe_opportunity = {
            "token": probe_token.symbol,
            "buy_dex": "aggregator",
            "sell_dex": "aggregator",
            "reason": reason,
        }
        try:
            probe_execution = self._execute_roundtrip(probe_token, self.config.idle_probe_amount_usd, label="probe")
        except Exception as exc:
            probe_execution = {"status": "failed", "error": str(exc), "profit_usd": "0", "label": "probe"}
            self._record_event("cycle_probe_error", {"opportunity": probe_opportunity, "error": str(exc)})
        self._update_stats(probe_opportunity, probe_execution)
        outcome = {"opportunity": probe_opportunity, "execution": probe_execution}
        self._record_event("cycle_probe", outcome)
        return outcome

    def run_cycle(self) -> Dict[str, Any]:
        self.state["cycles"] += 1
        if time.time() < self.rate_limited_until:
            if self._probe_allowed():
                return self._run_probe_cycle(reason="rate_limited_cooldown")
            remaining = max(1, int(self.rate_limited_until - time.time()))
            result = {"status": "rate_limited", "message": f"Cooling down for {remaining}s after OKX API 429"}
            self._record_event("cycle_rate_limited", result)
            return result
        opportunity = self.scan_best_opportunity()
        if not opportunity:
            if self._probe_allowed():
                reason = "rate_limited_after_scan" if time.time() < self.rate_limited_until else "no_opportunity"
                return self._run_probe_cycle(reason=reason)
            if time.time() < self.rate_limited_until:
                remaining = max(1, int(self.rate_limited_until - time.time()))
                result = {"status": "rate_limited", "message": f"Cooling down for {remaining}s after OKX API 429"}
                self._record_event("cycle_rate_limited", result)
                return result
            result = {"status": "idle", "message": "No opportunity above thresholds"}
            self._record_event("cycle_idle", result)
            return result

        execution: Optional[Dict[str, Any]] = None
        try:
            execution = self.execute(opportunity)
        except Exception as exc:
            execution = {"status": "failed", "error": str(exc), "profit_usd": "0"}

        self._update_stats(opportunity, execution)
        outcome = {"opportunity": opportunity, "execution": execution}
        self._record_event("cycle_result", outcome)
        return outcome

    def print_banner(self) -> None:
        print("=" * 72)
        print("FlashArb | Moltbook-native X Layer arbitrage agent")
        print("=" * 72)
        print(f"Mode: {self.config.mode}")
        print(f"Execution backend: {self.execution_backend}")
        print(f"Chain: X Layer ({self.config.chain_id})")
        print(f"Base token: {self.base_token.symbol if self.base_token else self.config.base_token}")
        print(f"Targets: {', '.join(token.symbol for token in self.target_tokens)}")
        print(f"DEXes: {', '.join(f'{name}:{dex_id}' for name, dex_id in self.dex_map.items())}")
        print(f"Trade amount: ${self.config.trade_amount}")
        print(f"Min profit: ${self.config.min_profit_usd} | Min spread: {self.config.min_spread_pct}%")
        print("=" * 72)

    def print_result(self, outcome: Dict[str, Any]) -> None:
        execution = outcome.get("execution")
        if not execution:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {outcome.get('status', 'idle')} | {outcome.get('message', 'no trade')}")
            return
        opportunity = outcome["opportunity"]
        estimated = opportunity.get("estimated_profit_usd", "n/a")
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"{opportunity['token']} {opportunity['buy_dex']}->{opportunity['sell_dex']} "
            f"est=${estimated} status={execution.get('status')} "
            f"realized=${execution.get('profit_usd', '0')}"
        )

    def print_stats(self) -> None:
        uptime = time.time() - self.state["start_time"]
        print("\n" + "=" * 72)
        print("FlashArb Statistics")
        print("=" * 72)
        print(f"Uptime: {uptime/60:.1f} min")
        print(f"Cycles: {self.state['cycles']}")
        print(f"Trades: {self.state['total_trades']}")
        print(f"Success: {self.state['successful']} | Failed: {self.state['failed']}")
        print(f"Profit: ${self.state['total_profit']}")
        print(f"Recent log: {self.event_log_path}")
        print("=" * 72)

    def run(self, once: bool = False) -> None:
        self.initialize()
        self.print_banner()
        while True:
            outcome = self.run_cycle()
            self.print_result(outcome)
            self._maybe_post_update()
            if once:
                if not self.last_post_at:
                    self._maybe_post_update(force=True)
                self.print_stats()
                return
            if self.state["cycles"] % 10 == 0:
                self.print_stats()
            time.sleep(self.config.check_interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlashArb X Layer runtime")
    parser.add_argument("--live", action="store_true", help="Execute real approvals and swaps")
    parser.add_argument("--once", action="store_true", help="Run a single scan cycle")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config = FlashArbConfig.from_env(live=args.live)
    if args.live:
        config.mode = "live"
    bot = FlashArbBot(config)
    try:
        bot.run(once=args.once)
    except KeyboardInterrupt:
        bot.print_stats()
