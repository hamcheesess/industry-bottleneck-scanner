from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .aggregation import AccelerationSnapshot, ClusterSnapshot, compare_windows, summarize
from .models import AtomicSignal


@dataclass(frozen=True)
class DiscoveryAggregationResult:
    current_signals: tuple[AtomicSignal, ...]
    baseline_signals: tuple[AtomicSignal, ...]
    current_clusters: tuple[ClusterSnapshot, ...]
    acceleration: tuple[AccelerationSnapshot, ...]

    @property
    def triggered_clusters(self) -> tuple[AccelerationSnapshot, ...]:
        return tuple(item for item in self.acceleration if item.triggered)

    @property
    def confirmed_clusters(self) -> tuple[AccelerationSnapshot, ...]:
        return tuple(item for item in self.acceleration if item.confirmed)


def aggregate_signal_windows(
    signals: Iterable[AtomicSignal],
    *,
    baseline_start: datetime,
    current_start: datetime,
    current_end: datetime | None = None,
) -> DiscoveryAggregationResult:
    """Bridge accepted AtomicSignals into cross-company Phase-1 acceleration.

    The baseline window is ``[baseline_start, current_start)`` and the current window is
    ``[current_start, current_end)``. When ``current_end`` is omitted, all later signals are
    included. Review candidates never reach this function unless they were explicitly
    accepted and promoted to AtomicSignals first.
    """

    if baseline_start >= current_start:
        raise ValueError("baseline_start must be earlier than current_start")
    if current_end is not None and current_end <= current_start:
        raise ValueError("current_end must be later than current_start")

    baseline: list[AtomicSignal] = []
    current: list[AtomicSignal] = []
    for signal in signals:
        published_at = signal.published_at
        if baseline_start <= published_at < current_start:
            baseline.append(signal)
            continue
        if published_at >= current_start and (current_end is None or published_at < current_end):
            current.append(signal)

    return DiscoveryAggregationResult(
        current_signals=tuple(current),
        baseline_signals=tuple(baseline),
        current_clusters=tuple(summarize(current)),
        acceleration=tuple(compare_windows(current, baseline)),
    )
