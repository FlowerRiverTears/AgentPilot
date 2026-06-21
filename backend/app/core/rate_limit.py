"""Simple in-memory rate limiter for login protection."""
import time
from collections import defaultdict

from app.core.config import settings


class LoginRateLimiter:
    """Sliding window rate limiter for login attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_limited(self, key: str) -> bool:
        """Check if the key is currently rate limited."""
        if not settings.rate_limit_enabled:
            return False
        now = time.time()
        # Clean old attempts
        self._attempts[key] = [
            t for t in self._attempts[key]
            if now - t < self.window_seconds
        ]
        return len(self._attempts[key]) >= self.max_attempts

    def record(self, key: str) -> None:
        """Record a login attempt."""
        if settings.rate_limit_enabled:
            self._attempts[key].append(time.time())

    def get_remaining_time(self, key: str) -> int:
        """Get seconds until the rate limit expires."""
        if not self._attempts[key]:
            return 0
        oldest = min(self._attempts[key])
        return max(0, int(self.window_seconds - (time.time() - oldest)))


login_limiter = LoginRateLimiter()
