from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import cast

from industry_bottleneck_scanner.aggregation import AccelerationSnapshot
from industry_bottleneck_scanner.causal_diagnosis import diagnose_market_trigger
from industry_bottleneck_scanner.market_trigger import IndustryMarketTrigger
from industry_bottleneck_scanner.models import AtomicSignal, Classification, SourceDocument
from industry_bottleneck_scanner.operating_support import build_operating_support


AS_OF = datetime(2026, 8, 21, 20, 0, tzinfo=timezone.utc)
BUCKET = "Electrical Equipment"


def document(
    company_id: str,
    *,
    age_days: int = 10,
    document_type: str = "sec_8k",
    future: bool = False,
) -> SourceDocument:
    published_at = AS_OF + timedelta(days=1) if future else AS_OF - timedelta(days=age_days)
    return SourceDocument(
        document_id=f"doc-{company_id}-{age_days}-{future}",
        company_id=company_id,
        ticker=company_id.upper(),
        document_type=document_type,
        published_at=published_at,
        text="Capacity remains constrained.",
        classification=Classification(industry=BUCKET),
        source_url="https://example.com/disclosure",
    )


def signal(item: SourceDocument) -> AtomicSignal:
    return AtomicSignal(
        signal_id=f"signal-{item.document_id}",
        scanner="scarcity",
        metric="capacity_constraint",
        direction="strengthening",
        magnitude="unknown",
        company_id=item.company_id,
        ticker=item.ticker,
        classification=item.classification,
        subject=None,
        document_id=item.document_id,
        document_type=item.document_type,
        published_at=item.published_at,
        source_url=item.source_url,
        evidence_text=item.text,
        negated=False,
        resolved=False,
        extraction_method="keyword",
        confidence=0.8,
    )


def market() -> IndustryMarketTrigger:
    return IndustryMarketTrigger(
        bucket=BUCKET,
        company_count=4,
        market_outperform_breadth=0.75,
        sector_outperform_breadth=0.75,
        near_high_breadth=0.5,
        abnormal_volume_breadth=0.5,
        median_market_relative_3m=0.1,
        median_sector_relative_3m=0.08,
        score=70,
        triggered=True,
        reasons=(),
    )


@dataclass
class FakeAcceleration:
    bucket: str = BUCKET
    confirmed: bool = False
    triggered: bool = False
    watchlisted: bool = False
    change_reasons: tuple[str, ...] = ()


def acceleration(**kwargs) -> AccelerationSnapshot:
    return cast(AccelerationSnapshot, FakeAcceleration(**kwargs))


def test_one_sided_multi_company_evidence_is_provider_independent_early_support() -> None:
    fresh = (document("a"), document("b"), document("c"))
    support = build_operating_support(
        bucket=BUCKET,
        as_of=AS_OF,
        expected_company_ids=("a", "b", "c", "d"),
        documents=fresh,
        signals=(signal(fresh[0]), signal(fresh[1])),
    )

    assert support.stage == "one_sided_strengthening"
    assert support.fresh_coverage_ratio == 0.75
    assert support.active_company_ids == ("a", "b")
    assert support.timing.trigger_era_documents == 3

    diagnosis = diagnose_market_trigger(market(), support=support)
    assert diagnosis.classification == "mixed_or_early"
    assert diagnosis.operating_stage == "one_sided_strengthening"


def test_stale_and_future_documents_are_explicitly_excluded_from_coverage() -> None:
    fresh = document("a", age_days=10)
    stale = document("b", age_days=200, document_type="sec_8k")
    future = document("c", future=True)
    support = build_operating_support(
        bucket=BUCKET,
        as_of=AS_OF,
        expected_company_ids=("a", "b", "c"),
        documents=(fresh, stale, future),
        signals=(signal(fresh), signal(stale), signal(future)),
    )

    assert support.fresh_company_ids == ("a",)
    assert support.stale_document_ids == (stale.document_id,)
    assert support.future_document_ids == (future.document_id,)
    assert support.active_signal_ids == (signal(fresh).signal_id,)
    assert support.timing.stale_documents == 1
    assert support.timing.future_documents == 1

    diagnosis = diagnose_market_trigger(market(), support=support)
    assert diagnosis.classification == "unresolved"
    assert "insufficient_operating_coverage" in diagnosis.reasons


def test_comparable_acceleration_remains_reusable_inside_operating_support() -> None:
    documents = tuple(document(company) for company in ("a", "b", "c"))
    support = build_operating_support(
        bucket=BUCKET,
        as_of=AS_OF,
        expected_company_ids=("a", "b", "c"),
        documents=documents,
        signals=(),
        comparable_acceleration=acceleration(confirmed=True, triggered=True),
    )

    assert support.stage == "comparable_confirmed"
    diagnosis = diagnose_market_trigger(market(), support=support)
    assert diagnosis.classification == "structural_operating"
    assert diagnosis.operating_stage == "comparable_confirmed"
