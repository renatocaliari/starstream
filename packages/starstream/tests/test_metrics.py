# tests/test_metrics.py
import pytest
from starstream.metrics import BroadcastMetrics


def test_metrics_initial_state():
    metrics = BroadcastMetrics()
    stats = metrics.get_stats()

    assert stats["success"] == 0
    assert stats["error"] == 0


def test_metrics_record_success():
    metrics = BroadcastMetrics()
    metrics.record_success(0.050)  # 50ms

    stats = metrics.get_stats()
    assert stats["success"] == 1
    assert stats["avg_latency_ms"] == 50.0


def test_metrics_record_error():
    metrics = BroadcastMetrics()
    metrics.record_error()

    stats = metrics.get_stats()
    assert stats["error"] == 1


def test_metrics_p95_latency():
    metrics = BroadcastMetrics()

    # Record 20 samples with increasing latency
    for i in range(20):
        metrics.record_success(i * 0.01)  # 0ms to 190ms

    stats = metrics.get_stats()
    # p95 of 0-190ms should be around 180ms
    assert stats["p95_latency_ms"] is not None
    assert stats["p95_latency_ms"] > 150
