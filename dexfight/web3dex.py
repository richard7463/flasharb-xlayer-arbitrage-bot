"""
web3dex - Web3 DEX Interface Library
Adapted for X Layer
"""

import json
import asyncio
from typing import Dict, List, Optional
from eth_account import Account
from web3 import Web3
from web3.contract import Contract

# X Layer configuration
from config_xlayer import CHAIN, DEX_CONFIGS, TOKENS, BASE_TOKEN

class Dex:
    """Base class for DEX interactions"""

    PLATFORM = ""

    # Simplified ABI for DEX Router
    ROUTER_ABI = json.loads('''[
        {"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_WETH9","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"inputs":[],"name":"WETH9","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"components":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"}],"internalType":"struct ISwapRouter.ExactInputParams","name":"params","type":"tuple"}],"name":"exactInput","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"},
        {"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}
    ]''')

    ERC20_ABI = json.loads('''[
        {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
    ]''')

    def __init__(self, rpc_url: str = None, private_key: str = ""):
        self.rpc_url = rpc_url or CHAIN["rpc_url"]
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
            self.address = self.account.address

        # Get DEX config
        self.config = DEX_CONFIGS.get(self.PLATFORM, {})
        self.router_address = self.config.get("router", "")
        self.factory_address = self.config.get("factory", "")

        # Token addresses
        self.base_address = BASE_TOKEN["address"]
        self.token = TOKENS.get("WIF", {}).get("address", "")

        # Router contract
        if self.router_address:
            self.router = self.w3.eth.contract(
                address=self.router_address,
                abi=self.ROUTER_ABI
            )
        else:
            self.router = None

    @property
    def platform(self) -> str:
        return self.PLATFORM

    def _get_token_contract(self, token_address: str) -> Contract:
        """Get ERC20 token contract"""
        return self.w3.eth.contract(address=token_address, abi=self.ERC20_ABI)

    def _get_reserves(self, token_a: str, token_b: str) -> tuple:
        """Get pair reserves (mock for now)"""
        # In production: query pair contract
        # For demo: return mock values
        import random
        return (random.uniform(10000, 100000), random.uniform(10000, 100000))

    def price(self, token_in, token_out, intermediate=None) -> float:
        """Get current price"""
        reserve_in, reserve_out = self._get_reserves(token_in, token_out)
        if reserve_in == 0:
            return 0
        return reserve_out / reserve_in

    def liquidity_in(self, token_in, token_out, intermediate=None) -> float:
        """Get liquidity for input token"""
        reserve_in, _ = self._get_reserves(token_in, token_out)
        return reserve_in

    def liquidity_out(self, token_in, token_out, intermediate=None) -> float:
        """Get liquidity for output token"""
        _, reserve_out = self._get_reserves(token_in, token_out)
        return reserve_out

    def reserve_ratio(self, token_in, token_out, intermediate=None, refresh=False) -> float:
        """Reserve ratio"""
        liq_in = self.liquidity_in(token_in, token_out, intermediate)
        liq_out = self.liquidity_out(token_in, token_out, intermediate)
        if liq_in == 0:
            return 0
        return liq_out / liq_in

    def fees(self, token_in, token_out, intermediate=None) -> float:
        """Trading fees"""
        return 0.003  # 0.3%

    def exist(self, token_in, token_out, intermediate=None) -> bool:
        """Check if pair exists"""
        # In production: check factory
        return True

    def balance(self, wallet: str, token: str) -> float:
        """Get wallet balance"""
        if token == self.base_address or token is None:
            # Native balance
            balance_wei = self.w3.eth.get_balance(wallet)
            return self.w3.from_wei(balance_wei, "ether")
        else:
            # ERC20 balance
            contract = self._get_token_contract(token)
            balance_wei = contract.functions.balanceOf(wallet).call()
            return balance_wei / 1e6  # Assuming USDC

    def check_approval(self, wallet: str, token: str) -> bool:
        """Check if token is approved for router"""
        if token == self.base_address:
            return True
        contract = self._get_token_contract(token)
        allowance = contract.functions.allowance(wallet, self.router_address).call()
        return allowance > 0

    def approve(self, token: str, wallet: str) -> Dict:
        """Approve token for router"""
        if token == self.base_address:
            return {"hash": "0x" + "a" * 64, "nonce": 0}

        contract = self._get_token_contract(token)
        tx = contract.functions.approve(
            self.router_address,
            2**256 - 1  # Max approval
        ).build_transaction({
            "from": wallet,
            "nonce": self.w3.eth.get_transaction_count(wallet),
            "gas": 100000,
            "gasPrice": self.w3.eth.gas_price,
        })

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

        return {"hash": tx_hash.hex(), "nonce": tx["nonce"]}

    def _build_swap_tx(self, token_in: str, token_out: str, amount: float, wallet: str, in_base: bool = True) -> Dict:
        """Build swap transaction"""
        if not self.router:
            return {"error": "No router"}

        amount_wei = int(amount * 1e6)  # USDC decimals

        # Get amount out minimum with slippage
        amount_out_min = int(amount_wei * 0.995)  # 0.5% slippage

        deadline = self.w3.eth.get_block('latest').timestamp + 600

        if in_base:
            # Swap USDC -> Token
            params = {
                "tokenIn": token_in,
                "tokenOut": token_out,
                "fee": 3000,
                "recipient": wallet,
                "deadline": deadline,
                "amountIn": amount_wei,
                "amountOutMinimum": amount_out_min,
                "sqrtPriceLimitX96": 0,
            }
        else:
            # Swap Token -> USDC
            params = {
                "tokenIn": token_in,
                "tokenOut": token_out,
                "fee": 3000,
                "recipient": wallet,
                "deadline": deadline,
                "amountIn": int(amount),
                "amountOutMinimum": amount_out_min,
                "sqrtPriceLimitX96": 0,
            }

        tx = self.router.functions.exactInputSingle(params).build_transaction({
            "from": wallet,
            "nonce": self.w3.eth.get_transaction_count(wallet),
            "gas": 300000,
            "gasPrice": self.w3.eth.gas_price,
        })

        return tx

    def swap_from_base_to_tokens(self, amount: float, token: str, wallet: str, intermediate=None, nonce=None, in_base=True) -> Dict:
        """Swap base token (USDC) to target token"""
        token_out = TOKENS.get(token, {}).get("address", token)
        if not in_base:
            token_out = self.base_address

        return self._build_swap_tx(self.base_address, token_out, amount, wallet, in_base)

    def swap_from_tokens_to_base(self, amount: float, token: str, wallet: str, intermediate=None, nonce=None, in_base=True) -> Dict:
        """Swap target token to base token (USDC)"""
        token_in = TOKENS.get(token, {}).get("address", token)
        if not in_base:
            token_in = self.base_address

        return self._build_swap_tx(token_in, self.base_address, amount, wallet, in_base)

    def sign_transaction(self, transaction: Dict, private_key: str) -> Dict:
        """Sign transaction"""
        if not self.account:
            return transaction

        signed = self.account.sign_transaction(transaction)
        return {**transaction, "signed": signed}

    def send_transaction(self, signed_transaction: Dict) -> str:
        """Send transaction"""
        if "signed" in signed_transaction:
            tx_hash = self.w3.eth.send_raw_transaction(signed_transaction["signed"].rawTransaction)
            return tx_hash.hex()
        return "0x" + "a" * 64

    def wait_transaction(self, tx_hash: str, timeout: int = 300) -> bool:
        """Wait for transaction confirmation"""
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return receipt.status == 1
        except:
            return True  # Assume success for demo


# DEX Implementations
class UniswapV3(Dex):
    PLATFORM = "uniswap_v3"


class Sushiswap(Dex):
    PLATFORM = "sushiswap"


class Pancakeswap(Dex):
    PLATFORM = "pancakeswap"


class OKX(Dex):
    PLATFORM = "okx"


# Registry
all = {
    "xlayer": [UniswapV3, Sushiswap, Pancakeswap, OKX],
}

# Export
__all__ = ["Dex", "UniswapV3", "Sushiswap", "Pancakeswap", "OKX", "all"]
