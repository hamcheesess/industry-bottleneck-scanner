from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal

from .models import AtomicSignal

AggregationLevel = Literal["sector", "industry", "subindustry"]


@dataclass(frozen=True)
class PrevalenceSnapshot:
    name: str
    companies: int


@dataclass(frozen=True)
class PrevalenceDelta:
    name: str
    current_companies: int
    baseline_companies: int
    change: int


@dataclass(frozen=True)
class ClusterSnapshot:
    bucket: str
    aggregation_level: AggregationLevel
    distinct_companies: int
    distinct_documents: int
    active_categories: tuple[str, ...]
    active_metrics: tuple[str, ...]
    category_prevalence: tuple[PrevalenceSnapshot, ...]
    metric_prevalence: tuple[PrevalenceSnapshot, ...]
    company_metric_pairs: int
    company_category_pairs: int
    source_types: tuple[str, ...]
    source_sections: tuple[str, ...]
    prepared_signals: int
    qa_signals: int
    qa_share: float
    strengthening_signals: int
    weakening_signals: int
    confidence_mean: float
    weighted_signal_count: float


@dataclass(frozen=True)
class AccelerationSnapshot:
    bucket: str
    aggregation_level: AggregationLevel
    eligible_companies: int
    breadth_current: int
    breadth_baseline: int
    breadth_change: int
    breadth_ratio: float | None
    category_breadth: int
    metric_breadth: int
    source_type_breadth: int
    metric_prevalence_deltas: tuple[PrevalenceDelta, ...]
    metric_prevalence_gains: tuple[str, ...]
    metric_prevalence_gain_count: int
    category_prevalence_deltas: tuple[PrevalenceDelta, ...]
    category_prevalence_gains: tuple[str, ...]
    category_prevalence_gain_count: int
    new_metrics: tuple[str, ...]
    company_metric_intensity_current: float
    company_metric_intensity_baseline: float
    company_metric_intensity_change: float
    qa_share_current: float
    qa_share_baseline: float
    qa_share_change: float
    core_pair_present: bool
    confirmation_count: int
    confidence_mean: float
    breadth_accelerating: bool
    prevalence_accelerating: bool
    change_reasons: tuple[str, ...]
    watch_blockers: tuple[str, ...]
    watchlisted: bool
    watch_reasons: tuple[str, ...]
    triggered: bool
    confirmed: bool


def _bucket(signal: AtomicSignal, aggregation_level: AggregationLevel) -> str:
    classification = signal.classification
    if aggregation_level == "sector":
        return classification.sector or classification.industry or classification.subindustry or "unclassified"
    if aggregation_level == "subindustry":
        return classification.subindustry or classification.industry or classification.sector or "unclassified"
    return classification.industry or classification.subindustry or classification.sector or "unclassified"


def _is_active_strengthening(signal: AtomicSignal) -> bool:
    return not signal.negated and not signal.resolved and signal.direction == "strengthening"


def _prevalence(items: Iterable[AtomicSignal], attribute: str) -> tuple[PrevalenceSnapshot, ...]:
    companies_by_name: dict[str, set[str]] = defaultdict(set)
    for item in items:
        companies_by_name[str(getattr(item, attribute))].add(item.company_id)
    return tuple(
        PrevalenceSnapshot(name=name, companies=len(companies))
        for name, companies in sorted(companies_by_name.items())
    )


def summarize(
    signals: list[AtomicSignal],
    *,
    aggregation_level: AggregationLevel = "industry",
) -> list[ClusterSnapshot]:
    """Summarize active and counter-evidence by an explicit classification level."""

    grouped: dict[str, list[AtomicSignal]] = defaultdict(list)
    for signal in signals:
        grouped[_bucket(signal, aggregation_level)].append(signal)

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
        category_prevalence = _prevalence(active, "scanner")
        metric_prevalence = _prevalence(active, "metric")
        company_metric_pairs = len({(item.company_id, item.metric) for item in active})
        company_category_pairs = len({(item.company_id, item.scanner) for item in active})
        source_types = tuple(sorted({item.document_type for item in active}))
        source_sections = tuple(sorted({item.source_section for item in active if item.source_section}))
        prepared_signals = sum(item.source_section == "prepared" for item in active)
        qa_signals = sum(item.source_section == "qa" for item in active)
        section_labeled = prepared_signals + qa_signals
        qa_share = qa_signals / section_labeled if section_labeled else 0.0
        confidence_mean = sum(item.confidence for item in active) / len(active) if active else 0.0
        weighted_signal_count = sum(item.confidence for item in active)

        snapshots.append(
            ClusterSnapshot(
                bucket=bucket,
                aggregation_level=aggregation_level,
                distinct_companies=len(companies),
                distinct_documents=len(documents),
                active_categories=categories,
                active_metrics=metrics,
                category_prevalence=category_prevalence,
                metric_prevalence=metric_prevalence,
                company_metric_pairs=company_metric_pairs,
                company_category_pairs=company_category_pairs,
                source_types=source_types,
                source_sections=source_sections,
                prepared_signals=prepared_signals,
                qa_signals=qa_signals,
                qa_share=qa_share,
                strengthening_signals=len(active),
                weakening_signals=len(weakening),
                confidence_mean=confidence_mean,
                weighted_signal_count=weighted_signal_count,
            )
        )
    return snapshots


def _prevalence_map(items: tuple[PrevalenceSnapshot, ...]) -> dict[str, int]:
    return {item.name: item.companies for item in items}


def _prevalence_deltas(
    current: dict[str, int],
    baseline: dict[str, int],
) -> tuple[PrevalenceDelta, ...]:
    return tuple(
        PrevalenceDelta(
            name=name,
            current_companies=current.get(name, 0),
            baseline_companies=baseline.get(name, 0),
            change=current.get(name, 0) - baseline.get(name, 0),
        )
        for name in sorted(set(current) | set(baseline))
    )


def compare_windows(
    current: list[AtomicSignal],
    baseline: list[AtomicSignal],
    *,
    aggregation_level: AggregationLevel = "industry",
    eligible_company_ids: Iterable[str] | None = None,
    min_companies: int = 3,
    min_categories: int = 2,
    min_confidence: float = 0.65,
    require_core_pair: bool = True,
    min_confirmation_categories: int = 1,
    min_metric_prevalence_gains: int = 2,
    min_company_metric_intensity_change: float = 0.25,
) -> list[AccelerationSnapshot]:
    """Compare matched windows using breadth plus company-level prevalence acceleration.

    Raw mention counts are deliberately excluded from the trigger. `change_reasons` records
    weak observed changes unconditionally. `watch_reasons` is populated only when a cluster
    actually qualifies for the watchlist, while `watch_blockers` explains which structural
    gates prevented watchlisting. This separation is diagnostic only and does not relax any
    trigger or watchlist threshold.
    """

    current_by_bucket = {
        snapshot.bucket: snapshot
        for snapshot in summarize(current, aggregation_level=aggregation_level)
    }
    baseline_by_bucket = {
        snapshot.bucket: snapshot
        for snapshot in summarize(baseline, aggregation_level=aggregation_level)
    }
    buckets = sorted(set(current_by_bucket) | set(baseline_by_bucket))
    if eligible_company_ids is None:
        eligible = {item.company_id for item in current} | {item.company_id for item in baseline}
    else:
        eligible = set(eligible_company_ids)
    eligible_count = len(eligible)

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

        current_metric = _prevalence_map(cur.metric_prevalence) if cur else {}
        baseline_metric = _prevalence_map(base.metric_prevalence) if base else {}
        metric_prevalence_deltas = _prevalence_deltas(current_metric, baseline_metric)
        metric_prevalence_gains = tuple(item.name for item in metric_prevalence_deltas if item.change > 0)
        new_metrics = tuple(
            item.name
            for item in metric_prevalence_deltas
            if item.current_companies > 0 and item.baseline_companies == 0
        )

        current_category = _prevalence_map(cur.category_prevalence) if cur else {}
        baseline_category = _prevalence_map(base.category_prevalence) if base else {}
        category_prevalence_deltas = _prevalence_deltas(current_category, baseline_category)
        category_prevalence_gains = tuple(
            item.name for item in category_prevalence_deltas if item.change > 0
        )

        current_pairs = cur.company_metric_pairs if cur else 0
        baseline_pairs = base.company_metric_pairs if base else 0
        denominator = eligible_count or max(breadth_current, breadth_baseline, 1)
        company_metric_intensity_current = current_pairs / denominator
        company_metric_intensity_baseline = baseline_pairs / denominator
        company_metric_intensity_change = company_metric_intensity_current - company_metric_intensity_baseline

        qa_share_current = cur.qa_share if cur else 0.0
        qa_share_baseline = base.qa_share if base else 0.0
        qa_share_change = qa_share_current - qa_share_baseline

        core_pair_present = {"demand", "scarcity"}.issubset(categories)
        confirmation_count = len(categories & {"capex", "pricing"})
        core_requirement_met = core_pair_present or not require_core_pair
        breadth_accelerating = breadth_change > 0
        prevalence_accelerating = (
            len(metric_prevalence_gains) >= min_metric_prevalence_gains
            and company_metric_intensity_change >= min_company_metric_intensity_change
        )
        acceleration_present = breadth_accelerating or prevalence_accelerating

        triggered = (
            breadth_current >= min_companies
            and acceleration_present
            and category_breadth >= min_categories
            and confidence_mean >= min_confidence
            and core_requirement_met
        )
        confirmed = triggered and confirmation_count >= min_confirmation_categories

        change_reasons_list: list[str] = []
        if breadth_accelerating:
            change_reasons_list.append("breadth_gain")
        if metric_prevalence_gains:
            change_reasons_list.append("metric_prevalence_gain")
        if new_metrics:
            change_reasons_list.append("new_metric")
        if company_metric_intensity_change > 0:
            change_reasons_list.append("company_metric_intensity_gain")

        watch_blockers_list: list[str] = []
        if breadth_current < min_companies:
            watch_blockers_list.append("min_breadth")
        if category_breadth < min_categories:
            watch_blockers_list.append("min_category_breadth")
        if confidence_mean < min_confidence:
            watch_blockers_list.append("min_confidence")
        if not core_requirement_met:
            watch_blockers_list.append("core_pair")

        watchlisted = (
            not triggered
            and not watch_blockers_list
            and bool(change_reasons_list)
        )
        watch_reasons = tuple(change_reasons_list) if watchlisted else ()

        results.append(
            AccelerationSnapshot(
                bucket=bucket,
                aggregation_level=aggregation_level,
                eligible_companies=eligible_count,
                breadth_current=breadth_current,
                breadth_baseline=breadth_baseline,
                breadth_change=breadth_change,
                breadth_ratio=breadth_ratio,
                category_breadth=category_breadth,
                metric_breadth=metric_breadth,
                source_type_breadth=source_type_breadth,
                metric_prevalence_deltas=metric_prevalence_deltas,
                metric_prevalence_gains=metric_prevalence_gains,
                metric_prevalence_gain_count=len(metric_prevalence_gains),
                category_prevalence_deltas=category_prevalence_deltas,
                category_prevalence_gains=category_prevalence_gains,
                category_prevalence_gain_count=len(category_prevalence_gains),
                new_metrics=new_metrics,
                company_metric_intensity_current=company_metric_intensity_current,
                company_metric_intensity_baseline=company_metric_intensity_baseline,
                company_metric_intensity_change=company_metric_intensity_change,
                qa_share_current=qa_share_current,
                qa_share_baseline=qa_share_baseline,
                qa_share_change=qa_share_change,
                core_pair_present=core_pair_present,
                confirmation_count=confirmation_count,
                confidence_mean=confidence_mean,
                breadth_accelerating=breadth_accelerating,
                prevalence_accelerating=prevalence_accelerating,
                change_reasons=tuple(change_reasons_list),
                watch_blockers=tuple(watch_blockers_list),
                watchlisted=watchlisted,
                watch_reasons=watch_reasons,
                triggered=triggered,
                confirmed=confirmed,
            )
        )
    return results
