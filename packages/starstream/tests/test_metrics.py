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


def test_metrics_boundary_19_samples():
    """p95 should not be calculated with less than 20 samples."""
    metrics = BroadcastMetrics()
    for i in range(19):
        metrics.record_success(i * 0.01)
    stats = metrics.get_stats()
    assert "p95_latency_ms" not in stats


def test_metrics_exactly_20_samples():
    """p95 should be calculated with exactly 20 samples."""
    metrics = BroadcastMetrics()
    for i in range(20):
        metrics.record_success(i * 0.01)
    stats = metrics.get_stats()
    assert "p95_latency_ms" in stats
    assert stats["p95_latency_ms"] >= 0


def test_metrics_interleaved_operations():
    """Test mixing success and error recordings."""
    metrics = BroadcastMetrics()
    metrics.record_success(0.01)
    metrics.record_error()
    metrics.record_success(0.02)
    metrics.record_error()

    stats = metrics.get_stats()
    assert stats["success"] == 2
    assert stats["error"] == 2
    assert stats["avg_latency_ms"] == 15.0
