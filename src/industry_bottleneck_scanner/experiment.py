from __future__ import annotations

from dataclasses import dataclass

from .aggregation import AccelerationSnapshot, AggregationLevel, summarize
from .batch_orchestration import BatchScanResult, compare_cached_batches, scan_cached_batch
from .company_metadata import CompanyPeriodMetadata
from .review_queue import FileReviewQueue
from .semantic_retrieval import LocalSemanticRetriever
from .transcript_store import FileTranscriptStore


@dataclass(frozen=True)
class CohortDiagnostics:
    requested_current: int
    requested_baseline: int
    metadata_matched: int
    eligible_companies: int
    current_only_company_ids: tuple[str, ...]
    baseline_only_company_ids: tuple[str, ...]
    current_missing_cache_ids: tuple[str, ...]
    baseline_missing_cache_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComparableExperimentResult:
    current: BatchScanResult
    baseline: BatchScanResult
    acceleration: tuple[AccelerationSnapshot, ...]
    diagnostics: CohortDiagnostics


def _index_unique(records: tuple[CompanyPeriodMetadata, ...], window: str) -> dict[str, CompanyPeriodMetadata]:
    indexed: dict[str, CompanyPeriodMetadata] = {}
    for record in records:
        if record.company_id in indexed:
            raise ValueError(f"{window} metadata contains duplicate company_id {record.company_id!r}")
        indexed[record.company_id] = record
    return indexed


def _filter_batch(
    result: BatchScanResult,
    eligible: set[str],
    *,
    aggregation_level: AggregationLevel,
) -> BatchScanResult:
    signals = tuple(signal for signal in result.signals if signal.company_id in eligible)
    companies = tuple(company for company in result.companies if company.company_id in eligible)
    return BatchScanResult(
        signals=signals,
        companies=companies,
        clusters=tuple(summarize(list(signals), aggregation_level=aggregation_level)),
        missing_transcripts=0,
        review_candidates=sum(company.review_count for company in companies),
        aggregation_level=aggregation_level,
    )


def run_comparable_cached_experiment(
    current_records: tuple[CompanyPeriodMetadata, ...],
    baseline_records: tuple[CompanyPeriodMetadata, ...],
    *,
    provider: str,
    transcript_store: FileTranscriptStore,
    semantic_retriever: LocalSemanticRetriever | None = None,
    review_queue: FileReviewQueue | None = None,
    max_companies: int | None = None,
    aggregation_level: AggregationLevel = "industry",
) -> ComparableExperimentResult:
    """Run a cache-only current-vs-baseline experiment on a matched issuer cohort.

    The cohort is aligned twice: first by metadata presence in both windows, then by
    successful cached transcript availability in both windows. This prevents changes in
    provider coverage or cache completeness from being misread as breadth acceleration.
    """

    if max_companies is not None and max_companies < 1:
        raise ValueError("max_companies must be at least 1")

    current_by_id = _index_unique(current_records, "current")
    baseline_by_id = _index_unique(baseline_records, "baseline")
    current_ids = set(current_by_id)
    baseline_ids = set(baseline_by_id)
    common_ids = current_ids & baseline_ids

    ordered_common = [record.company_id for record in current_records if record.company_id in common_ids]
    if max_companies is not None:
        ordered_common = ordered_common[:max_companies]

    current_selected = tuple(current_by_id[company_id] for company_id in ordered_common)
    baseline_selected = tuple(baseline_by_id[company_id] for company_id in ordered_common)

    current_raw = scan_cached_batch(
        current_selected,
        provider=provider,
        transcript_store=transcript_store,
        semantic_retriever=semantic_retriever,
        review_queue=review_queue,
        aggregation_level=aggregation_level,
    )
    baseline_raw = scan_cached_batch(
        baseline_selected,
        provider=provider,
        transcript_store=transcript_store,
        semantic_retriever=semantic_retriever,
        review_queue=review_queue,
        aggregation_level=aggregation_level,
    )

    current_scanned = {item.company_id for item in current_raw.companies if item.status == "scanned"}
    baseline_scanned = {item.company_id for item in baseline_raw.companies if item.status == "scanned"}
    eligible = current_scanned & baseline_scanned

    current = _filter_batch(current_raw, eligible, aggregation_level=aggregation_level)
    baseline = _filter_batch(baseline_raw, eligible, aggregation_level=aggregation_level)
    acceleration = compare_cached_batches(
        current,
        baseline,
        aggregation_level=aggregation_level,
    )

    diagnostics = CohortDiagnostics(
        requested_current=len(current_records),
        requested_baseline=len(baseline_records),
        metadata_matched=len(ordered_common),
        eligible_companies=len(eligible),
        current_only_company_ids=tuple(sorted(current_ids - baseline_ids)),
        baseline_only_company_ids=tuple(sorted(baseline_ids - current_ids)),
        current_missing_cache_ids=tuple(
            sorted(item.company_id for item in current_raw.companies if item.status == "missing_cache")
        ),
        baseline_missing_cache_ids=tuple(
            sorted(item.company_id for item in baseline_raw.companies if item.status == "missing_cache")
        ),
    )
    return ComparableExperimentResult(
        current=current,
        baseline=baseline,
        acceleration=acceleration,
        diagnostics=diagnostics,
    )
