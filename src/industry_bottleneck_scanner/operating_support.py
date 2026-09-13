from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal

from .aggregation import AccelerationSnapshot
from .models import AtomicSignal, SourceDocument

OperatingSupportStage = Literal[
    "no_support",
    "observing",
    "one_sided_strengthening",
    "comparable_partial",
    "comparable_triggered",
    "comparable_confirmed",
]


@dataclass(frozen=True)
class OperatingEvidencePolicy:
    default_max_age_days: int = 450
    recent_update_days: int = 120
    trigger_era_days: int = 14
    min_one_sided_companies: int = 2
    max_age_days_by_type: tuple[tuple[str, int], ...] = (
        ("earnings_call_turn", 180),
        ("earnings_release", 180),
        ("investor_presentation", 180),
        ("sec_10k", 450),
        ("sec_10q", 180),
        ("sec_8k", 120),
        ("sec_8k_exhibit", 180),
    )

    def __post_init__(self) -> None:
        if self.default_max_age_days < 0:
            raise ValueError("default_max_age_days must be non-negative")
        if not 0 <= self.trigger_era_days <= self.recent_update_days:
            raise ValueError("trigger_era_days must not exceed recent_update_days")
        if self.min_one_sided_companies < 1:
            raise ValueError("min_one_sided_companies must be positive")
        if any(days < 0 for _, days in self.max_age_days_by_type):
            raise ValueError("document max ages must be non-negative")

    def max_age_days(self, document_type: str) -> int:
        return dict(self.max_age_days_by_type).get(document_type, self.default_max_age_days)


@dataclass(frozen=True)
class EvidenceTimingSummary:
    pre_existing_documents: int
    recent_update_documents: int
    trigger_era_documents: int
    stale_documents: int
    future_documents: int


@dataclass(frozen=True)
class OperatingSupport:
    bucket: str
    as_of: datetime
    expected_company_ids: tuple[str, ...]
    document_company_ids: tuple[str, ...]
    fresh_company_ids: tuple[str, ...]
    fresh_document_ids: tuple[str, ...]
    stale_document_ids: tuple[str, ...]
    future_document_ids: tuple[str, ...]
    active_signal_ids: tuple[str, ...]
    active_company_ids: tuple[str, ...]
    source_types: tuple[str, ...]
    timing: EvidenceTimingSummary
    stage: OperatingSupportStage
    reasons: tuple[str, ...]
    comparable_acceleration: AccelerationSnapshot | None = None

    @property
    def fresh_coverage_ratio(self) -> float:
        if not self.expected_company_ids:
            return 0.0
        return len(self.fresh_company_ids) / len(self.expected_company_ids)

    @property
    def source_type_breadth(self) -> int:
        return len(self.source_types)


def _signal_bucket(signal: AtomicSignal) -> str:
    classification = signal.classification
    return (
        classification.industry
        or classification.subindustry
        or classification.sector
        or "unclassified"
    )


def _active_strengthening(signal: AtomicSignal) -> bool:
    return signal.direction == "strengthening" and not signal.negated and not signal.resolved


def build_operating_support(
    *,
    bucket: str,
    as_of: datetime,
    expected_company_ids: Iterable[str],
    documents: Iterable[SourceDocument],
    signals: Iterable[AtomicSignal],
    comparable_acceleration: AccelerationSnapshot | None = None,
    policy: OperatingEvidencePolicy = OperatingEvidencePolicy(),
) -> OperatingSupport:
    """Fuse fresh one-sided evidence and optional comparable acceleration by references."""

    if as_of.tzinfo is None:
        raise ValueError("OperatingSupport.as_of must be timezone-aware")
    expected = tuple(sorted(set(expected_company_ids)))
    if not bucket.strip():
        raise ValueError("bucket is required")
    if comparable_acceleration is not None and comparable_acceleration.bucket != bucket:
        raise ValueError("comparable acceleration bucket does not match OperatingSupport bucket")

    document_items = tuple(documents)
    document_ids = [item.document_id for item in document_items]
    if len(set(document_ids)) != len(document_ids):
        raise ValueError("OperatingSupport documents must have unique document IDs")

    expected_set = set(expected)
    known_document_companies: set[str] = set()
    fresh_companies: set[str] = set()
    fresh_document_ids: set[str] = set()
    stale_document_ids: set[str] = set()
    future_document_ids: set[str] = set()
    source_types: set[str] = set()
    pre_existing = 0
    recent_update = 0
    trigger_era = 0

    for document in document_items:
        if document.published_at.tzinfo is None:
            raise ValueError(f"document {document.document_id} published_at must be timezone-aware")
        if document.company_id not in expected_set:
            continue
        if document.published_at > as_of:
            future_document_ids.add(document.document_id)
            continue
        known_document_companies.add(document.company_id)
        age_days = (as_of - document.published_at).total_seconds() / 86400
        if age_days > policy.max_age_days(document.document_type):
            stale_document_ids.add(document.document_id)
            continue
        fresh_document_ids.add(document.document_id)
        fresh_companies.add(document.company_id)
        source_types.add(document.document_type)
        if age_days <= policy.trigger_era_days:
            trigger_era += 1
        elif age_days <= policy.recent_update_days:
            recent_update += 1
        else:
            pre_existing += 1

    active_signals: dict[str, AtomicSignal] = {}
    for signal in signals:
        if signal.published_at.tzinfo is None:
            raise ValueError(f"signal {signal.signal_id} published_at must be timezone-aware")
        if signal.document_id not in fresh_document_ids:
            continue
        if signal.company_id not in expected_set or _signal_bucket(signal) != bucket:
            continue
        if _active_strengthening(signal):
            active_signals.setdefault(signal.signal_id, signal)
    active_companies = {signal.company_id for signal in active_signals.values()}

    reasons: list[str] = []
    if comparable_acceleration is not None and comparable_acceleration.confirmed:
        stage: OperatingSupportStage = "comparable_confirmed"
        reasons.append("comparable_acceleration_confirmed")
    elif comparable_acceleration is not None and comparable_acceleration.triggered:
        stage = "comparable_triggered"
        reasons.append("comparable_acceleration_triggered")
    elif comparable_acceleration is not None and (
        comparable_acceleration.watchlisted or comparable_acceleration.change_reasons
    ):
        stage = "comparable_partial"
        reasons.append("comparable_operating_change_partial")
    elif len(active_companies) >= policy.min_one_sided_companies:
        stage = "one_sided_strengthening"
        reasons.append("multi_company_one_sided_strengthening")
    elif active_signals:
        stage = "observing"
        reasons.append("single_company_or_sparse_strengthening")
    else:
        stage = "no_support"
        reasons.append("no_active_fresh_operating_signal")

    if stale_document_ids:
        reasons.append("stale_documents_excluded")
    if future_document_ids:
        reasons.append("future_documents_excluded")

    return OperatingSupport(
        bucket=bucket,
        as_of=as_of,
        expected_company_ids=expected,
        document_company_ids=tuple(sorted(known_document_companies)),
        fresh_company_ids=tuple(sorted(fresh_companies)),
        fresh_document_ids=tuple(sorted(fresh_document_ids)),
        stale_document_ids=tuple(sorted(stale_document_ids)),
        future_document_ids=tuple(sorted(future_document_ids)),
        active_signal_ids=tuple(sorted(active_signals)),
        active_company_ids=tuple(sorted(active_companies)),
        source_types=tuple(sorted(source_types)),
        timing=EvidenceTimingSummary(
            pre_existing_documents=pre_existing,
            recent_update_documents=recent_update,
            trigger_era_documents=trigger_era,
            stale_documents=len(stale_document_ids),
            future_documents=len(future_document_ids),
        ),
        stage=stage,
        reasons=tuple(reasons),
        comparable_acceleration=comparable_acceleration,
    )
