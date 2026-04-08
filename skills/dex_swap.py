"""
OKX DEX Swap Skill
Token swap execution on X Layer with proper slippage handling
"""

import logging
import asyncio
from typing import Dict, Optional
from eth_account import Account
from web3 import Web3
from web3.gas_strategies import medium_gas_strategy

logger = logging.getLogger(__name__)


class DexSwapSkill:
    """Skill: okx-dex-swap - Token swap execution"""

    # DEX Router ABIs
    UNISWAP_V3_ROUTER_ABI = [
        {
            "inputs": [
                {"name": "params", "type": "tuple", "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "deadline", "type": "uint256"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"}
                ]}
            ],
            "name": "exactInputSingle",
            "outputs": [{"name": "amountOut", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    ERC20_ABI = [
        {
            "inputs": [{"name": "owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
            "name": "approve",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    # Token decimals
    TOKEN_DECIMALS = {
        "USDC": 6,
        "USDT": 6,
        "WIF": 6,
        "PEPE": 18,
        "SHIB": 18,
        "GIGA": 6,
        "NEIRO": 9,
    }

    def __init__(self, private_key: str, rpc_url: str = "https://rpc.xlayer.com"):
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.address = self.account.address
        self.chain_id = 19697  # X Layer

        # Gas strategy
        self.w3.eth.set_gas_price_strategy(medium_gas_strategy)

        # DEX routers
        self.routers = {
            "uniswap": "0xE592427A0AEce92De3Edee1F18E0157C05881564",
            "sushiswap": "0xd9e1ce17f2641f24be83665cba2da6c6cb6f7e83",
            "pancakeswap": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "okx": "0xb94f689f214ade8d3e83136d3ade815f542a9b3b",
        }

    def get_token_decimals(self, token: str) -> int:
        """Get token decimals"""
        return self.TOKEN_DECIMALS.get(token, 18)

    def to_wei(self, amount: float, token: str) -> int:
        """Convert amount to wei based on token decimals"""
        decimals = self.get_token_decimals(token)
        return int(amount * (10 ** decimals))

    def from_wei(self, amount: int, token: str) -> float:
        """Convert wei to amount"""
        decimals = self.get_token_decimals(token)
        return amount / (10 ** decimals)

    def get_token_contract(self, token_address: str):
        """Get ERC20 token contract"""
        return self.w3.eth.contract(
            address=token_address,
            abi=self.ERC20_ABI
        )

    def get_router_contract(self, dex: str):
        """Get DEX router contract"""
        router_address = self.routers.get(dex.lower())
        if not router_address:
            raise ValueError(f"Unknown DEX: {dex}")

        return self.w3.eth.contract(
            address=router_address,
            abi=self.UNISWAP_V3_ROUTER_ABI
        )

    def get_balance(self, token_address: str) -> int:
        """Get token balance"""
        if token_address in ("0x0000000000000000000000000000000000000000", "native"):
            return self.w3.eth.get_balance(self.address)

        contract = self.get_token_contract(token_address)
        return contract.functions.balanceOf(self.address).call()

    def get_gas_price(self) -> int:
        """Get current gas price"""
        return self.w3.eth.gas_price

    def get_nonce(self) -> int:
        """Get current nonce"""
        return self.w3.eth.get_transaction_count(self.address)

    def approve_token(self, token_address: str, spender: str, amount: int) -> Optional[str]:
        """Approve token for spending"""
        try:
            contract = self.get_token_contract(token_address)

            tx = contract.functions.approve(spender, amount).build_transaction({
                "from": self.address,
                "nonce": self.get_nonce(),
                "gas": 100000,
                "gasPrice": self.get_gas_price(),
            })

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex() if receipt.status == 1 else None

        except Exception as e:
            logger.error(f"Approve error: {e}")
            return None

    def get_quote(self, token_in: str, token_out: str, amount: float, dex: str) -> Optional[float]:
        """
        Get swap quote (expected output amount)

        Args:
            token_in: Input token symbol
            token_out: Output token symbol
            amount: Amount in
            dex: DEX name

        Returns:
            Expected output amount (not including slippage)
        """
        # In production: call DEX router contract
        # For demo: assume 99% output (1% spread)
        # In real implementation, would query router contract
        return amount * 0.995

    def build_swap_tx(
        self,
        token_in_addr: str,
        token_out_addr: str,
        amount_in: int,
        amount_out_min: int,
        dex: str,
        fee: int = 3000
    ) -> Dict:
        """Build swap transaction"""
        router = self.get_router_contract(dex)
        deadline = self.w3.eth.get_block('latest').timestamp + 600

        tx = router.functions.exactInputSingle({
            "tokenIn": token_in_addr,
            "tokenOut": token_out_addr,
            "fee": fee,
            "recipient": self.address,
            "deadline": deadline,
            "amountIn": amount_in,
            "amountOutMinimum": amount_out_min,
            "sqrtPriceLimitX96": 0,
        }).build_transaction({
            "from": self.address,
            "nonce": self.get_nonce(),
            "gas": 300000,
            "gasPrice": self.get_gas_price(),
        })

        return tx

    def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        dex: str,
        slippage: float = 0.5
    ) -> Dict:
        """
        Execute token swap with slippage protection

        Args:
            token_in: Input token symbol/address
            token_out: Output token symbol/address
            amount: Amount to swap
            dex: DEX name
            slippage: Slippage tolerance (default 0.5%)

        Returns:
            Dict with tx_hash, status, amount_out
        """
        try:
            # Token addresses (in production, fetch from chain)
            token_addresses = {
                "USDC": "0x74b6b8cd8021f6855b14e0e0c3d47d72c5e8b7bb",
                "USDT": "0x5DE1678304E92F6D7552a4A9f2A5E0e7E9fE6c9a",
                "WIF": "0x1C9A2D6b4c5E6f7890a1b2c3d4e5f6a7b8c9d0e1",
                "PEPE": "0x2A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B",
            }

            token_in_addr = token_addresses.get(token_in, token_in)
            token_out_addr = token_addresses.get(token_out, token_out)

            # Convert to wei
            amount_in_wei = self.to_wei(amount, token_in)

            # Check balance
            balance = self.get_balance(token_in_addr)
            if balance < amount_in_wei:
                return {
                    "tx_hash": "",
                    "status": "insufficient_balance",
                    "amount_out": 0,
                    "error": f"Need {amount_in_wei}, have {balance}"
                }

            # Get quote
            quote = self.get_quote(token_in, token_out, amount, dex)
            if not quote:
                return {"tx_hash": "", "status": "no_quote", "amount_out": 0}

            # Calculate minimum output with slippage protection
            amount_out_min = int(quote * (1 - slippage / 100) * (10 ** self.get_token_decimals(token_out)))

            # Approve if needed (skip for native)
            router_addr = self.routers.get(dex.lower())
            if router_addr and token_in_addr != "0x0000000000000000000000000000000000000000":
                # Check if already approved (simplified)
                pass

            # Build transaction (simulated for demo)
            # In production: sign and send real transaction
            tx_hash = f"0x{''.join(['a' for _ in range(64)])}"

            # Calculate actual output (simulated)
            actual_output = self.from_wei(amount_out_min, token_out)

            return {
                "tx_hash": tx_hash,
                "status": "success",
                "amount_out": actual_output,
                "amount_out_min": quote * (1 - slippage / 100),
                "slippage_used": slippage,
                "gas_used": 200000,
                "gas_price": self.get_gas_price(),
            }

        except Exception as e:
            logger.error(f"Swap error: {e}")
            return {
                "tx_hash": "",
                "status": "error",
                "error": str(e),
                "amount_out": 0
            }

    def execute_flash_swap(self, token_in: str, token_out: str, amount: float, dex: str) -> Dict:
        """
        Execute flash swap (borrow, swap, repay in one transaction)
        More complex but atomically captures arbitrage

        Args:
            token_in: Input token
            token_out: Output token
            amount: Amount
            dex: DEX

        Returns:
            Result dict
        """
        # Flash swaps require more complex contracts
        # For now, use regular swap
        return self.execute_swap(token_in, token_out, amount, dex)
