from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .aggregation import AccelerationSnapshot
from .discovery_score import DiscoveryScore, score_acceleration
from .models import AtomicSignal


@dataclass(frozen=True)
class EvidenceReference:
    signal_id: str
    company_id: str
    ticker: str | None
    metric: str
    scanner: str
    published_at: str
    document_id: str
    evidence_text: str
    confidence: float


@dataclass(frozen=True)
class DiscoveryHandoffRecord:
    schema_version: str
    generated_at: str
    bucket: str
    aggregation_level: str
    stage: str
    discovery_score: float
    breadth_current: int
    breadth_baseline: int
    metric_prevalence_gains: tuple[str, ...]
    core_pair_present: bool
    confirmation_count: int
    company_ids: tuple[str, ...]
    tickers: tuple[str, ...]
    evidence: tuple[EvidenceReference, ...]


def build_handoff_record(
    snapshot: AccelerationSnapshot,
    current_signals: tuple[AtomicSignal, ...],
    *,
    generated_at: datetime | None = None,
    max_evidence: int = 12,
) -> DiscoveryHandoffRecord:
    """Build a compact Repo-A output without performing downstream underwriting.

    The contract intentionally carries discovery evidence and acceleration state only.
    It contains no valuation, financial-risk decision, DCF fields, or investment verdict.
    """

    if max_evidence < 1:
        raise ValueError("max_evidence must be at least 1")

    score: DiscoveryScore = score_acceleration(snapshot)
    relevant = [
        signal
        for signal in current_signals
        if not signal.negated and not signal.resolved and signal.direction == "strengthening"
    ]
    relevant.sort(key=lambda item: (-item.confidence, item.company_id, item.signal_id))
    company_ids = tuple(sorted({item.company_id for item in relevant}))
    tickers = tuple(sorted({item.ticker for item in relevant if item.ticker}))
    evidence = tuple(
        EvidenceReference(
            signal_id=item.signal_id,
            company_id=item.company_id,
            ticker=item.ticker,
            metric=item.metric,
            scanner=item.scanner,
            published_at=item.published_at.isoformat(),
            document_id=item.document_id,
            evidence_text=item.evidence_text,
            confidence=item.confidence,
        )
        for item in relevant[:max_evidence]
    )
    now = generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")

    return DiscoveryHandoffRecord(
        schema_version="0.1",
        generated_at=now.isoformat(),
        bucket=snapshot.bucket,
        aggregation_level=snapshot.aggregation_level,
        stage=score.stage,
        discovery_score=score.score,
        breadth_current=snapshot.breadth_current,
        breadth_baseline=snapshot.breadth_baseline,
        metric_prevalence_gains=snapshot.metric_prevalence_gains,
        core_pair_present=snapshot.core_pair_present,
        confirmation_count=snapshot.confirmation_count,
        company_ids=company_ids,
        tickers=tickers,
        evidence=evidence,
    )


def handoff_to_dict(record: DiscoveryHandoffRecord) -> dict[str, object]:
    return asdict(record)
