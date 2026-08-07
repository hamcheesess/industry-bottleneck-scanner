from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .aggregation import AccelerationSnapshot, ClusterSnapshot, compare_windows, summarize
from .company_metadata import CompanyPeriodMetadata
from .discovery_pipeline import scan_earnings_call
from .models import AtomicSignal
from .review_queue import FileReviewQueue
from .semantic_retrieval import LocalSemanticRetriever
from .transcript_store import FileTranscriptStore


@dataclass(frozen=True)
class BatchCompanyResult:
    ticker: str
    quarter: str
    status: str
    signal_count: int = 0
    review_count: int = 0


@dataclass(frozen=True)
class BatchScanResult:
    signals: tuple[AtomicSignal, ...]
    companies: tuple[BatchCompanyResult, ...]
    clusters: tuple[ClusterSnapshot, ...]
    missing_transcripts: int
    review_candidates: int


def scan_cached_batch(
    records: tuple[CompanyPeriodMetadata, ...],
    *,
    provider: str,
    transcript_store: FileTranscriptStore,
    semantic_retriever: LocalSemanticRetriever | None = None,
    review_queue: FileReviewQueue | None = None,
    max_companies: int | None = None,
) -> BatchScanResult:
    """Scan a bounded batch of already-cached transcripts without provider calls.

    This is intentionally cache-only. Data acquisition and signal extraction remain
    separate operational stages so re-running research never consumes provider quota.
    """

    if max_companies is not None and max_companies < 0:
        raise ValueError("max_companies must be non-negative")

    selected = records if max_companies is None else records[:max_companies]
    all_signals: list[AtomicSignal] = []
    companies: list[BatchCompanyResult] = []
    total_review = 0
    missing = 0

    for record in selected:
        transcript = transcript_store.load(
            provider=provider,
            ticker=record.ticker,
            quarter=record.quarter,
        )
        if transcript is None:
            missing += 1
            companies.append(BatchCompanyResult(record.ticker, record.quarter, "missing_cache"))
            continue

        result = scan_earnings_call(
            transcript,
            company_id=record.company_id,
            published_at=record.published_at,
            classification=record.classification,
            semantic_retriever=semantic_retriever,
            review_queue=review_queue,
        )
        all_signals.extend(result.signals)
        total_review += len(result.review_candidates)
        companies.append(
            BatchCompanyResult(
                ticker=record.ticker,
                quarter=record.quarter,
                status="scanned",
                signal_count=len(result.signals),
                review_count=len(result.review_candidates),
            )
        )

    signals = tuple(all_signals)
    return BatchScanResult(
        signals=signals,
        companies=tuple(companies),
        clusters=tuple(summarize(list(signals))),
        missing_transcripts=missing,
        review_candidates=total_review,
    )


def compare_cached_batches(
    current: BatchScanResult,
    baseline: BatchScanResult,
) -> tuple[AccelerationSnapshot, ...]:
    return tuple(compare_windows(list(current.signals), list(baseline.signals)))
