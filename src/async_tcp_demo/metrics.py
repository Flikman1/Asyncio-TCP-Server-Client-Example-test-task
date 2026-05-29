"""Metrics collection utilities for the asyncio TCP demo."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from statistics import fmean


@dataclass(slots=True)
class MetricsCollector:
    """Collect basic client-side networking metrics."""

    sent_pings: int = 0
    received_pongs: int = 0
    timeouts: int = 0
    retries: int = 0
    reconnects: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record_ping_sent(self) -> None:
        self.sent_pings += 1

    def record_pong_received(self, latency_ms: float) -> None:
        self.received_pongs += 1
        self.latencies_ms.append(latency_ms)

    def record_timeout(self) -> None:
        self.timeouts += 1

    def record_retry(self) -> None:
        self.retries += 1

    def record_reconnect(self) -> None:
        self.reconnects += 1

    @property
    def success_rate(self) -> float:
        if self.sent_pings == 0:
            return 0.0
        return self.received_pongs / self.sent_pings * 100.0

    @property
    def timeout_rate(self) -> float:
        if self.sent_pings == 0:
            return 0.0
        return self.timeouts / self.sent_pings * 100.0

    @property
    def average_latency(self) -> float | None:
        if not self.latencies_ms:
            return None
        return fmean(self.latencies_ms)

    @property
    def min_latency(self) -> float | None:
        if not self.latencies_ms:
            return None
        return min(self.latencies_ms)

    @property
    def max_latency(self) -> float | None:
        if not self.latencies_ms:
            return None
        return max(self.latencies_ms)

    @property
    def p95_latency(self) -> float | None:
        if not self.latencies_ms:
            return None
        ordered = sorted(self.latencies_ms)
        index = max(0, math.ceil(len(ordered) * 0.95) - 1)
        return ordered[index]

    def format_summary(self, *, clients: int | None = None) -> str:
        """Return a human-readable metrics summary."""

        average_latency = _format_latency(self.average_latency)
        min_latency = _format_latency(self.min_latency)
        max_latency = _format_latency(self.max_latency)
        p95_latency = _format_latency(self.p95_latency)

        lines = ["Demo summary", "------------"]
        if clients is not None:
            lines.append(f"Clients: {clients}")
        lines.extend(
            [
                f"Sent PING: {self.sent_pings}",
                f"Received PONG: {self.received_pongs}",
                f"Timeouts: {self.timeouts}",
                f"Retries: {self.retries}",
                f"Reconnects: {self.reconnects}",
                f"Success rate: {self.success_rate:.1f}%",
                f"Timeout rate: {self.timeout_rate:.1f}%",
                f"Average latency: {average_latency}",
                f"Min latency: {min_latency}",
                f"Max latency: {max_latency}",
                f"P95 latency: {p95_latency}",
            ]
        )
        return "\n".join(lines)


def merge_metrics(metrics: Iterable[MetricsCollector]) -> MetricsCollector:
    """Merge multiple metric collectors into one summary object."""

    merged = MetricsCollector()
    for collector in metrics:
        merged.sent_pings += collector.sent_pings
        merged.received_pongs += collector.received_pongs
        merged.timeouts += collector.timeouts
        merged.retries += collector.retries
        merged.reconnects += collector.reconnects
        merged.latencies_ms.extend(collector.latencies_ms)
    return merged


def _format_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} ms"
