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
    subindustry: str | None = None,
    confidence: float = 0.8,
    document_type: str = "10-Q",
    direction: str = "strengthening",
    resolved: bool = False,
    source_section: str | None = None,
) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner=scanner,  # type: ignore[arg-type]
        metric=metric,
        direction=direction,  # type: ignore[arg-type]
        magnitude="unknown",
        company_id=company_id,
        ticker=None,
        classification=Classification(industry=industry, subindustry=subindustry),
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
        source_section=source_section,
    )


def test_summary_prioritizes_distinct_company_breadth() -> None:
    signals = [
        _signal("1", "a", "scarcity", metric="lead_time_pressure"),
        _signal("2", "a", "scarcity", metric="capacity_constraint"),
        _signal("3", "b", "pricing", metric="pricing_power"),
    ]

    summary = summarize(signals)[0]
    assert summary.aggregation_level == "industry"
    assert summary.distinct_companies == 2
    assert summary.distinct_documents == 3
    assert summary.company_metric_pairs == 3
    assert {item.name: item.companies for item in summary.metric_prevalence} == {
        "capacity_constraint": 1,
        "lead_time_pressure": 1,
        "pricing_power": 1,
    }
    assert set(summary.active_categories) == {"scarcity", "pricing"}
    assert set(summary.active_metrics) == {
        "lead_time_pressure",
        "capacity_constraint",
        "pricing_power",
    }


def test_industry_default_does_not_fragment_related_subindustries() -> None:
    signals = [
        _signal("1", "a", "demand", subindustry="Power Management"),
        _signal("2", "b", "scarcity", subindustry="Connection & Protection"),
        _signal("3", "c", "pricing", subindustry="Utility Solutions"),
    ]

    industry = summarize(signals)
    subindustry = summarize(signals, aggregation_level="subindustry")

    assert len(industry) == 1
    assert industry[0].bucket == "Electrical Equipment"
    assert industry[0].distinct_companies == 3
    assert len(subindustry) == 3
    assert {item.aggregation_level for item in subindustry} == {"subindustry"}


def test_summary_reports_prepared_and_qa_evidence_separately() -> None:
    summary = summarize(
        [
            _signal("1", "a", "demand", source_section="prepared"),
            _signal("2", "b", "scarcity", source_section="qa"),
            _signal("3", "c", "pricing", source_section="qa"),
        ]
    )[0]

    assert summary.source_sections == ("prepared", "qa")
    assert summary.prepared_signals == 1
    assert summary.qa_signals == 2
    assert summary.qa_share == 2 / 3


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
    assert result.aggregation_level == "industry"
    assert result.breadth_current == 3
    assert result.breadth_change == 2
    assert result.breadth_accelerating is True
    assert result.core_pair_present is False
    assert result.watchlisted is False
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
    assert result.watchlisted is False
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


def test_flat_breadth_can_accelerate_when_multiple_metrics_spread_across_matched_companies() -> None:
    eligible = ("a", "b", "c", "d")
    baseline = [
        _signal("b1", "a", "demand", metric="backlog_strength"),
        _signal("b2", "b", "scarcity", metric="capacity_constraint"),
        _signal("b3", "c", "pricing", metric="pricing_power"),
        _signal("b4", "d", "demand", metric="backlog_strength"),
    ]
    current = [
        _signal("c1", "a", "demand", metric="backlog_strength"),
        _signal("c2", "b", "scarcity", metric="capacity_constraint"),
        _signal("c3", "c", "pricing", metric="pricing_power"),
        _signal("c4", "d", "demand", metric="backlog_strength"),
        _signal("c5", "c", "scarcity", metric="capacity_constraint"),
        _signal("c6", "d", "scarcity", metric="lead_time_pressure"),
        _signal("c7", "a", "scarcity", metric="lead_time_pressure"),
    ]

    result = compare_windows(current, baseline, eligible_company_ids=eligible)[0]

    assert result.breadth_current == 4
    assert result.breadth_baseline == 4
    assert result.breadth_change == 0
    assert result.breadth_accelerating is False
    assert result.metric_prevalence_gain_count >= 2
    assert result.company_metric_intensity_change >= 0.25
    assert result.prevalence_accelerating is True
    assert result.triggered is True
    assert result.confirmed is True


def test_single_metric_gain_is_watchlisted_without_relaxing_trigger() -> None:
    eligible = ("a", "b", "c", "d")
    baseline = [
        _signal("b1", "a", "demand", metric="backlog_strength"),
        _signal("b2", "b", "scarcity", metric="capacity_constraint"),
        _signal("b3", "c", "pricing", metric="pricing_power"),
        _signal("b4", "d", "demand", metric="bookings_strength"),
    ]
    current = baseline + [
        _signal("c1", "b", "demand", metric="backlog_strength"),
    ]

    result = compare_windows(current, baseline, eligible_company_ids=eligible)[0]

    assert result.breadth_change == 0
    assert result.metric_prevalence_gains == ("backlog_strength",)
    backlog = next(item for item in result.metric_prevalence_deltas if item.name == "backlog_strength")
    assert backlog.current_companies == 2
    assert backlog.baseline_companies == 1
    assert backlog.change == 1
    assert result.prevalence_accelerating is False
    assert result.watchlisted is True
    assert "metric_prevalence_gain" in result.watch_reasons
    assert result.triggered is False


def test_repeated_mentions_do_not_create_prevalence_acceleration_or_watchlist() -> None:
    eligible = ("a", "b", "c")
    baseline = [
        _signal("b1", "a", "demand", metric="backlog_strength"),
        _signal("b2", "b", "scarcity", metric="capacity_constraint"),
        _signal("b3", "c", "pricing", metric="pricing_power"),
    ]
    current = baseline + [
        _signal("c1", "a", "demand", metric="backlog_strength"),
        _signal("c2", "a", "demand", metric="backlog_strength"),
        _signal("c3", "a", "demand", metric="backlog_strength"),
    ]

    result = compare_windows(current, baseline, eligible_company_ids=eligible)[0]

    assert result.breadth_change == 0
    assert result.company_metric_intensity_change == 0.0
    assert result.metric_prevalence_gain_count == 0
    assert result.prevalence_accelerating is False
    assert result.watchlisted is False
    assert result.triggered is False
