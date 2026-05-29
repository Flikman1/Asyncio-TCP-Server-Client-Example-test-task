from __future__ import annotations

from async_tcp_demo.metrics import MetricsCollector


def test_success_rate_is_calculated() -> None:
    metrics = MetricsCollector(sent_pings=10, received_pongs=8)
    assert metrics.success_rate == 80.0


def test_timeout_rate_is_calculated() -> None:
    metrics = MetricsCollector(sent_pings=20, timeouts=5)
    assert metrics.timeout_rate == 25.0


def test_average_latency_is_calculated() -> None:
    metrics = MetricsCollector(latencies_ms=[100.0, 200.0, 300.0], received_pongs=3)
    assert metrics.average_latency == 200.0


def test_p95_latency_is_calculated() -> None:
    metrics = MetricsCollector(latencies_ms=[10.0, 20.0, 30.0, 40.0, 50.0], received_pongs=5)
    assert metrics.p95_latency == 50.0
