from datetime import datetime, timezone

from industry_bottleneck_scanner.aggregation import AccelerationSnapshot
from industry_bottleneck_scanner.handoff_contract import build_handoff_record, handoff_to_dict
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _snapshot() -> AccelerationSnapshot:
    return AccelerationSnapshot(
        bucket="Electrical Equipment",
        aggregation_level="industry",
        eligible_companies=3,
        breadth_current=3,
        breadth_baseline=1,
        breadth_change=2,
        breadth_ratio=3.0,
        category_breadth=3,
        metric_breadth=3,
        source_type_breadth=1,
        metric_prevalence_deltas=(),
        metric_prevalence_gains=("backlog_strength", "capacity_constraint"),
        metric_prevalence_gain_count=2,
        category_prevalence_deltas=(),
        category_prevalence_gains=("demand", "scarcity"),
        category_prevalence_gain_count=2,
        new_metrics=("capacity_constraint",),
        company_metric_intensity_current=1.5,
        company_metric_intensity_baseline=0.5,
        company_metric_intensity_change=1.0,
        qa_share_current=0.5,
        qa_share_baseline=0.2,
        qa_share_change=0.3,
        core_pair_present=True,
        confirmation_count=1,
        confidence_mean=0.84,
        breadth_accelerating=True,
        prevalence_accelerating=True,
        watchlisted=False,
        watch_reasons=("breadth_gain", "metric_prevalence_gain"),
        triggered=True,
        confirmed=True,
    )


def _signal(signal_id: str, company_id: str, ticker: str, confidence: float) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner="scarcity",
        metric="capacity_constraint",
        direction="strengthening",
        magnitude="unknown",
        company_id=company_id,
        ticker=ticker,
        classification=Classification(industry="Electrical Equipment"),
        subject=None,
        document_id=f"doc-{signal_id}",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="Capacity remains constrained.",
        negated=False,
        resolved=False,
        extraction_method="regex",
        confidence=confidence,
    )


def test_handoff_contains_discovery_evidence_without_underwriting_fields() -> None:
    record = build_handoff_record(
        _snapshot(),
        (_signal("1", "issuer-a", "AAA", 0.9), _signal("2", "issuer-b", "BBB", 0.8)),
        generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    payload = handoff_to_dict(record)

    assert payload["schema_version"] == "0.1"
    assert payload["stage"] == "confirmed"
    assert payload["company_ids"] == ("issuer-a", "issuer-b")
    assert payload["tickers"] == ("AAA", "BBB")
    assert len(payload["evidence"]) == 2
    assert "dcf" not in payload
    assert "valuation" not in payload
    assert "investment_verdict" not in payload


def test_handoff_requires_timezone_aware_generation_time() -> None:
    try:
        build_handoff_record(
            _snapshot(),
            (_signal("1", "issuer-a", "AAA", 0.9),),
            generated_at=datetime(2026, 8, 12),
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected timezone validation error")
