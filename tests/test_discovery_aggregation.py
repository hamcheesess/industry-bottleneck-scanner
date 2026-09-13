from datetime import datetime, timezone

from industry_bottleneck_scanner.discovery_aggregation import aggregate_signal_windows
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _signal(*, company: str, scanner: str, metric: str, when: datetime) -> AtomicSignal:
    return AtomicSignal(
        signal_id=f"{company}-{scanner}-{metric}-{when.date()}",
        scanner=scanner,
        metric=metric,
        direction="strengthening",
        magnitude="unknown",
        company_id=company,
        ticker=company.upper(),
        classification=Classification(industry="Electrical Equipment"),
        subject=None,
        document_id=f"doc-{company}-{scanner}-{when.date()}",
        document_type="earnings_call_turn",
        published_at=when,
        source_url=None,
        evidence_text="evidence",
        negated=False,
        resolved=False,
        extraction_method="keyword",
        confidence=0.9,
    )


def test_accepted_signals_flow_into_cross_company_acceleration() -> None:
    baseline_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    current_start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    signals = [
        _signal(company="a", scanner="demand", metric="backlog_strength", when=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        _signal(company="a", scanner="demand", metric="backlog_strength", when=datetime(2026, 5, 1, tzinfo=timezone.utc)),
        _signal(company="b", scanner="scarcity", metric="capacity_constraint", when=datetime(2026, 5, 2, tzinfo=timezone.utc)),
        _signal(company="c", scanner="pricing", metric="pricing_power", when=datetime(2026, 5, 3, tzinfo=timezone.utc)),
    ]

    result = aggregate_signal_windows(
        signals,
        baseline_start=baseline_start,
        current_start=current_start,
    )

    assert len(result.current_signals) == 3
    assert len(result.baseline_signals) == 1
    assert result.current_clusters[0].distinct_companies == 3
    assert result.acceleration[0].triggered is True
    assert result.acceleration[0].confirmed is True


def test_window_boundaries_are_validated() -> None:
    point = datetime(2026, 4, 1, tzinfo=timezone.utc)
    try:
        aggregate_signal_windows([], baseline_start=point, current_start=point)
    except ValueError as exc:
        assert "baseline_start" in str(exc)
    else:
        raise AssertionError("expected ValueError")
