from datetime import datetime, timezone

from industry_bottleneck_scanner.aggregation import compare_windows, summarize
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _signal(
    signal_id: str,
    company_id: str,
    scanner: str,
    *,
    metric: str = "metric",
    industry: str = "Electrical Equipment",
    confidence: float = 0.8,
    document_type: str = "10-Q",
    direction: str = "strengthening",
    resolved: bool = False,
) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner=scanner,  # type: ignore[arg-type]
        metric=metric,
        direction=direction,  # type: ignore[arg-type]
        magnitude="unknown",
        company_id=company_id,
        ticker=None,
        classification=Classification(industry=industry),
        subject=None,
        document_id=f"doc-{signal_id}",
        document_type=document_type,
        published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="evidence",
        negated=False,
        resolved=resolved,
        extraction_method="rule",
        confidence=confidence,
    )


def test_summary_prioritizes_distinct_company_breadth() -> None:
    signals = [
        _signal("1", "a", "scarcity", metric="lead_time_pressure"),
        _signal("2", "a", "scarcity", metric="capacity_constraint"),
        _signal("3", "b", "pricing", metric="pricing_power"),
    ]

    summary = summarize(signals)[0]
    assert summary.distinct_companies == 2
    assert summary.distinct_documents == 3
    assert set(summary.active_categories) == {"scarcity", "pricing"}
    assert set(summary.active_metrics) == {
        "lead_time_pressure",
        "capacity_constraint",
        "pricing_power",
    }


def test_weakening_evidence_does_not_inflate_active_breadth() -> None:
    signals = [
        _signal("1", "a", "scarcity"),
        _signal("2", "b", "scarcity", direction="weakening", resolved=True),
    ]

    summary = summarize(signals)[0]
    assert summary.distinct_companies == 1
    assert summary.strengthening_signals == 1
    assert summary.weakening_signals == 1


def test_research_trigger_requires_demand_and_scarcity_core_pair() -> None:
    baseline = [_signal("b1", "a", "scarcity")]
    current = [
        _signal("c1", "a", "scarcity"),
        _signal("c2", "b", "scarcity"),
        _signal("c3", "c", "pricing"),
    ]

    result = compare_windows(current, baseline)[0]
    assert result.breadth_current == 3
    assert result.breadth_change == 2
    assert result.core_pair_present is False
    assert result.triggered is False


def test_triggered_cluster_becomes_confirmed_with_pricing_or_capex() -> None:
    baseline = [_signal("b1", "a", "demand")]
    current = [
        _signal("c1", "a", "demand", metric="backlog_strength"),
        _signal("c2", "b", "scarcity", metric="lead_time_pressure"),
        _signal("c3", "c", "demand", metric="bookings_strength"),
        _signal("c4", "c", "pricing", metric="pricing_power", document_type="transcript"),
    ]

    result = compare_windows(current, baseline)[0]
    assert result.breadth_current == 3
    assert result.breadth_baseline == 1
    assert result.breadth_change == 2
    assert result.core_pair_present is True
    assert result.confirmation_count == 1
    assert result.source_type_breadth == 2
    assert result.metric_breadth == 4
    assert result.triggered is True
    assert result.confirmed is True


def test_core_pair_can_trigger_before_confirmation() -> None:
    baseline = []
    current = [
        _signal("c1", "a", "demand"),
        _signal("c2", "b", "scarcity"),
        _signal("c3", "c", "demand"),
    ]

    result = compare_windows(current, baseline)[0]
    assert result.triggered is True
    assert result.confirmed is False
