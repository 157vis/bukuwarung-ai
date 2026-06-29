"""In-memory rate limiter sederhana untuk FastAPI."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Token bucket per key (IP / user_id)."""

    max_requests: int = 30
    window_seconds: float = 60.0
    _hits: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = [t for t in self._hits[key] if t > window_start]
        if len(hits) >= self.max_requests:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = [t for t in self._hits[key] if t > window_start]
        return max(0, self.max_requests - len(hits))
