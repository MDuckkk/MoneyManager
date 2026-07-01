# -*- coding: utf-8 -*-
"""
Rate-limiter sliding-window trong tiến trình (concern: rate-limiting).

Thuần logic -> test offline 100% (truyền `now` để khỏi phụ thuộc đồng hồ thật).
Lưu ý: bộ nhớ in-process -> chỉ đúng cho 1 worker. Multi-worker production cần
limiter chia sẻ (Redis) — ngoài phạm vi POC (xem ghi chú scale ngang).
"""
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_per_window: int, window_s: float = 60.0):
        self.max = max_per_window
        self.window = window_s
        self._hits: dict[str, deque] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        """True nếu còn quota cho `key` trong cửa sổ; ghi nhận 1 hit khi cho phép."""
        if self.max <= 0:
            return True                     # 0 = tắt giới hạn
        now = time.time() if now is None else now
        dq = self._hits.setdefault(key, deque())
        cutoff = now - self.window
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= self.max:
            return False
        dq.append(now)
        return True

    def retry_after(self, key: str, now: float | None = None) -> float:
        """Số giây tới khi hit cũ nhất rời cửa sổ (gợi ý header Retry-After)."""
        dq = self._hits.get(key)
        if not dq:
            return 0.0
        now = time.time() if now is None else now
        return max(0.0, self.window - (now - dq[0]))
