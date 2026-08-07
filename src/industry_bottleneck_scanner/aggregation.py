from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .models import AtomicSignal


@dataclass(frozen=True)
class ClusterSnapshot:
    bucket: str
    distinct_companies: int
    distinct_documents: int
    active_categories: tuple[str, ...]
    strengthening_signals: int
    weakening_signals: int
    confidence_mean: float


@dataclass(frozen=True)
class AccelerationSnapshot:
    bucket: str
    breadth_current: int
    breadth_baseline: int
    breadth_change: int
    breadth_ratio: float | None
    category_breadth: int
    confidence_mean: float
    triggered: bool


def _bucket(signal: AtomicSignal) -> str:
    classification = signal.classification
    return classification.subindustry or classification.industry or classification.sector or "unclassified"


def summarize(signals: list[AtomicSignal]) -> list[ClusterSnapshot]:
    grouped: dict[str, list[AtomicSignal]] = defaultdict(list)
    for signal in signals:
        if signal.negated or signal.resolved:
            continue
        grouped[_bucket(signal)].append(signal)

    snapshots: list[ClusterSnapshot] = []
    for bucket, items in sorted(grouped.items()):
        companies = {item.company_id for item in items}
        documents = {item.document_id for item in items}
        categories = tuple(sorted({item.scanner for item in items}))
        strengthening = sum(item.direction == "strengthening" for item in items)
        weakening = sum(item.direction == "weakening" for item in items)
        confidence_mean = sum(item.confidence for item in items) / len(items)
        snapshots.append(
            ClusterSnapshot(
                bucket=bucket,
                distinct_companies=len(companies),
                distinct_documents=len(documents),
                active_categories=categories,
                strengthening_signals=strengthening,
                weakening_signals=weakening,
                confidence_mean=confidence_mean,
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
) -> list[AccelerationSnapshot]:
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
        category_breadth = len(cur.active_categories) if cur else 0
        confidence_mean = cur.confidence_mean if cur else 0.0
        triggered = (
            breadth_current >= min_companies
            and breadth_change > 0
            and category_breadth >= min_categories
            and confidence_mean >= min_confidence
        )
        results.append(
            AccelerationSnapshot(
                bucket=bucket,
                breadth_current=breadth_current,
                breadth_baseline=breadth_baseline,
                breadth_change=breadth_change,
                breadth_ratio=breadth_ratio,
                category_breadth=category_breadth,
                confidence_mean=confidence_mean,
                triggered=triggered,
            )
        )
    return results
