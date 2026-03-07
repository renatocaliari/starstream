"""
Broadcast metrics for monitoring and observability.
"""

from dataclasses import dataclass, field
from collections import deque


@dataclass
class BroadcastMetrics:
    """
    Simple metrics for broadcast operations.

    Tracks success/error counts and latency samples.
    KISS design: only essential metrics.
    """

    success_count: int = 0
    error_count: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_success(self, latency: float):
        """Record successful broadcast with latency in seconds."""
        self.success_count += 1
        self.latency_samples.append(latency)

    def record_error(self):
        """Record broadcast error."""
        self.error_count += 1

    def get_stats(self) -> dict:
        """Return statistics dictionary."""
        if not self.latency_samples:
            return {"success": self.success_count, "error": self.error_count}

        sorted_latencies = sorted(self.latency_samples)
        n = len(sorted_latencies)

        stats = {
            "success": self.success_count,
            "error": self.error_count,
            "avg_latency_ms": round(sum(sorted_latencies) / n * 1000, 2),
        }

        if n >= 20:
            stats["p95_latency_ms"] = round(sorted_latencies[int(n * 0.95)] * 1000, 2)

        return stats
