from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple


@dataclass
class RequestStats:
    latencies_ms: Deque[float]
    errors: int
    timeouts: int
    total: int


class MetricsRegistry:
    """In-memory metrics registry.

    - Per-path rolling latency window for p95 calculation
    - Error and timeout counters
    """

    def __init__(self, window_size: int = 200) -> None:
        self._window_size = window_size
        self._lock = threading.Lock()
        self._per_path: Dict[str, RequestStats] = defaultdict(
            lambda: RequestStats(latencies_ms=deque(maxlen=self._window_size), errors=0, timeouts=0, total=0)
        )

    def record(self, path: str, latency_ms: float, *, is_error: bool = False, is_timeout: bool = False) -> None:
        with self._lock:
            stats = self._per_path[path]
            stats.latencies_ms.append(latency_ms)
            stats.total += 1
            if is_error:
                stats.errors += 1
            if is_timeout:
                stats.timeouts += 1

    def snapshot(self) -> Dict[str, Dict[str, float | int]]:
        with self._lock:
            result: Dict[str, Dict[str, float | int]] = {}
            for path, stats in self._per_path.items():
                p95 = calculate_p95(list(stats.latencies_ms)) if stats.latencies_ms else 0.0
                result[path] = {
                    "p95_ms": round(p95, 2),
                    "count": stats.total,
                    "errors": stats.errors,
                    "timeouts": stats.timeouts,
                }
            return result


def calculate_p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = int(0.95 * (len(sorted_vals) - 1))
    return sorted_vals[k]


registry = MetricsRegistry()


