"""
Security Module
Pre-trade validation and risk management
"""

from typing import Dict
from skills.security import SecuritySkill


class SecurityModule:
    """Pre-trade security checks"""

    def __init__(self, security_api_key: str = ""):
        self.security = SecuritySkill(security_api_key)

    def validate_trade(self, token_address: str) -> Dict:
        """
        Full security validation for a trade

        Args:
            token_address: Token to trade

        Returns:
            Validation result with is_safe flag
        """
        scan = self.security.scan(token_address)

        is_safe = (
            scan["risk_level"] == "low" and
            not scan.get("honeypot", True) and
            scan.get("verified", False)
        )

        return {
            "is_safe": is_safe,
            "scan": scan,
            "can_trade": is_safe
        }

    def check_risk_score(self, token_address: str) -> float:
        """
        Get risk score (0-100)

        Args:
            token_address: Token address

        Returns:
            Risk score (lower is safer)
        """
        scan = self.security.scan(token_address)

        score = 0

        if scan.get("honeypot"):
            score += 50
        if scan.get("mintable"):
            score += 20
        if scan.get("blacklistable"):
            score += 20
        if not scan.get("verified"):
            score += 10
        if scan.get("risk_level") == "high":
            score += 30

        return min(score, 100)
