"""wokao.security.rate_limit — 进程内滑动窗口限流器（认证接口防爆破）。

本地单机应用定位：无需 Redis，内存实现即可；进程重启计数归零属可接受降级。
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple

_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = defaultdict(deque)
_MAX_TRACKED_KEYS = 10000


def allow(key: str, limit: int = 8, window_seconds: float = 300.0) -> bool:
    """key 在 window_seconds 内允许最多 limit 次；超出返回 False。线程安全。"""
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        cutoff = now - window_seconds
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        # 防内存膨胀：键总量超阈值时清理已过期窗口
        if len(_hits) > _MAX_TRACKED_KEYS:
            for k in [k for k, v in _hits.items() if not v or v[-1] <= cutoff]:
                _hits.pop(k, None)
        return True
