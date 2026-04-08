"""
OKX Wallet Skill
Wallet portfolio and balance management
"""

from typing import Dict, List, Optional
from web3 import Web3


class WalletSkill:
    """Skill: okx-wallet-portfolio - Balance check"""

    def __init__(self, private_key: str, rpc_url: str = "https://rpc.xlayer.com"):
        from eth_account import Account
        self.account = Account.from_key(private_key)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.address = self.account.address

    def get_native_balance(self) -> float:
        """
        Get native token (XLM/XETH) balance

        Returns:
            Balance in native token
        """
        balance_wei = self.w3.eth.get_balance(self.address)
        return self.w3.from_wei(balance_wei, "ether")

    def get_token_balance(self, token_address: str) -> float:
        """
        Get ERC20 token balance

        Args:
            token_address: Token contract address

        Returns:
            Token balance
        """
        # In production: call ERC20 balanceOf
        return 0.0

    def get_portfolio(self, tokens: List[str]) -> Dict:
        """
        Get full portfolio balances

        Args:
            tokens: List of token addresses

        Returns:
            Dict of token -> balance
        """
        portfolio = {
            "native": self.get_native_balance()
        }

        for token in tokens:
            portfolio[token] = self.get_token_balance(token)

        return portfolio

    def ensure_sufficient_balance(
        self,
        token: str,
        required_amount: float,
        gas_native: float = 0.01
    ) -> bool:
        """
        Check if wallet has sufficient balance

        Args:
            token: Token address
            required_amount: Required amount
            gas_native: Native token needed for gas

        Returns:
            True if sufficient
        """
        native_balance = self.get_native_balance()
        if native_balance < gas_native:
            return False

        if token.lower() != "native":
            token_balance = self.get_token_balance(token)
            return token_balance >= required_amount

        return native_balance >= required_amount + gas_native
