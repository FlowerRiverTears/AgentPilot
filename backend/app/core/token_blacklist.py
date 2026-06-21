"""Simple in-memory token blacklist for logout/token revocation."""
import time


class TokenBlacklist:
    """In-memory token blacklist. Tokens expire automatically based on their JWT exp claim."""

    def __init__(self):
        self._blacklist: dict[str, float] = {}  # jti -> exp_timestamp

    def add(self, jti: str, exp: float) -> None:
        """Add a token to the blacklist."""
        self._blacklist[jti] = exp

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted."""
        if jti not in self._blacklist:
            return False
        # Auto-cleanup expired entries
        if self._blacklist[jti] < time.time():
            del self._blacklist[jti]
            return False
        return True

    def cleanup(self) -> None:
        """Remove all expired entries from the blacklist."""
        now = time.time()
        expired = [jti for jti, exp in self._blacklist.items() if exp < now]
        for jti in expired:
            del self._blacklist[jti]


token_blacklist = TokenBlacklist()
