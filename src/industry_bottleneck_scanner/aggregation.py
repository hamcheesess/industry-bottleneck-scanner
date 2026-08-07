from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import AtomicSignal


@dataclass(frozen=True)
class ClusterSnapshot:
    bucket: str
    distinct_companies: int
    distinct_documents: int
    active_categories: tuple[str, ...]
    active_metrics: tuple[str, ...]
    source_types: tuple[str, ...]
    source_sections: tuple[str, ...]
    prepared_signals: int
    qa_signals: int
    strengthening_signals: int
    weakening_signals: int
    confidence_mean: float
    weighted_signal_count: float


@dataclass(frozen=True)
class AccelerationSnapshot:
    bucket: str
    breadth_current: int
    breadth_baseline: int
    breadth_change: int
    breadth_ratio: float | None
    category_breadth: int
    metric_breadth: int
    source_type_breadth: int
    core_pair_present: bool
    confirmation_count: int
    confidence_mean: float
    triggered: bool
    confirmed: bool


def _bucket(signal: AtomicSignal) -> str:
    classification = signal.classification
    return classification.subindustry or classification.industry or classification.sector or "unclassified"


def _is_active_strengthening(signal: AtomicSignal) -> bool:
    return not signal.negated and not signal.resolved and signal.direction == "strengthening"


def summarize(signals: list[AtomicSignal]) -> list[ClusterSnapshot]:
    """Summarize active and counter-evidence by classification bucket."""

    grouped: dict[str, list[AtomicSignal]] = defaultdict(list)
    for signal in signals:
        grouped[_bucket(signal)].append(signal)

    snapshots: list[ClusterSnapshot] = []
    for bucket, items in sorted(grouped.items()):
        active = [item for item in items if _is_active_strengthening(item)]
        weakening = [
            item
            for item in items
            if item.direction == "weakening" or item.negated or item.resolved
        ]

        companies = {item.company_id for item in active}
        documents = {item.document_id for item in active}
        categories = tuple(sorted({item.scanner for item in active}))
        metrics = tuple(sorted({item.metric for item in active}))
        source_types = tuple(sorted({item.document_type for item in active}))
        source_sections = tuple(sorted({item.source_section for item in active if item.source_section}))
        prepared_signals = sum(item.source_section == "prepared" for item in active)
        qa_signals = sum(item.source_section == "qa" for item in active)
        confidence_mean = (
            sum(item.confidence for item in active) / len(active) if active else 0.0
        )
        weighted_signal_count = sum(item.confidence for item in active)

        snapshots.append(
            ClusterSnapshot(
                bucket=bucket,
                distinct_companies=len(companies),
                distinct_documents=len(documents),
                active_categories=categories,
                active_metrics=metrics,
                source_types=source_types,
                source_sections=source_sections,
                prepared_signals=prepared_signals,
                qa_signals=qa_signals,
                strengthening_signals=len(active),
                weakening_signals=len(weakening),
                confidence_mean=confidence_mean,
                weighted_signal_count=weighted_signal_count,
            )
        )
    return snapshots


def compare_windows(
    current: list[AtomicSignal],
    baseline: list[AtomicSignal],
    *,
    min_companies: int = 3,
    min_categories: int = 2,
    min_confidence: float = 0.65,
    require_core_pair: bool = True,
    min_confirmation_categories: int = 1,
) -> list[AccelerationSnapshot]:
    """Compare current and baseline windows and emit auditable trigger components."""

    current_by_bucket = {snapshot.bucket: snapshot for snapshot in summarize(current)}
    baseline_by_bucket = {snapshot.bucket: snapshot for snapshot in summarize(baseline)}
    buckets = sorted(set(current_by_bucket) | set(baseline_by_bucket))

    results: list[AccelerationSnapshot] = []
    for bucket in buckets:
        cur = current_by_bucket.get(bucket)
        base = baseline_by_bucket.get(bucket)
        breadth_current = cur.distinct_companies if cur else 0
        breadth_baseline = base.distinct_companies if base else 0
        breadth_change = breadth_current - breadth_baseline
        breadth_ratio = None if breadth_baseline == 0 else breadth_current / breadth_baseline

        categories = set(cur.active_categories) if cur else set()
        category_breadth = len(categories)
        metric_breadth = len(cur.active_metrics) if cur else 0
        source_type_breadth = len(cur.source_types) if cur else 0
        confidence_mean = cur.confidence_mean if cur else 0.0

        core_pair_present = {"demand", "scarcity"}.issubset(categories)
        confirmation_count = len(categories & {"capex", "pricing"})
        core_requirement_met = core_pair_present or not require_core_pair

        triggered = (
            breadth_current >= min_companies
            and breadth_change > 0
            and category_breadth >= min_categories
            and confidence_mean >= min_confidence
            and core_requirement_met
        )
        confirmed = triggered and confirmation_count >= min_confirmation_categories

        results.append(
            AccelerationSnapshot(
                bucket=bucket,
                breadth_current=breadth_current,
                breadth_baseline=breadth_baseline,
                breadth_change=breadth_change,
                breadth_ratio=breadth_ratio,
                category_breadth=category_breadth,
                metric_breadth=metric_breadth,
                source_type_breadth=source_type_breadth,
                core_pair_present=core_pair_present,
                confirmation_count=confirmation_count,
                confidence_mean=confidence_mean,
                triggered=triggered,
                confirmed=confirmed,
            )
        )
    return results
