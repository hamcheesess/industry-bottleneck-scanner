from datetime import datetime, timezone

from industry_bottleneck_scanner.aggregation import compare_windows
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _signal(signal_id: str, company: str, scanner: str, metric: str) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner=scanner,  # type: ignore[arg-type]
        metric=metric,
        direction="strengthening",
        magnitude="unknown",
        company_id=company,
        ticker=company,
        classification=Classification(industry="Electrical Equipment"),
        subject=None,
        document_id=f"doc-{signal_id}",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="evidence",
        negated=False,
        resolved=False,
        extraction_method="keyword",
        confidence=0.8,
    )


def test_triggered_cluster_records_changes_but_not_watch_reasons() -> None:
    baseline = [
        _signal("b1", "A", "demand", "backlog_strength"),
        _signal("b2", "B", "scarcity", "capacity_constraint"),
        _signal("b3", "C", "pricing", "pricing_power"),
    ]
    current = baseline + [
        _signal("c1", "C", "demand", "bookings_strength"),
        _signal("c2", "A", "scarcity", "lead_time_pressure"),
    ]

    result = compare_windows(current, baseline, eligible_company_ids=("A", "B", "C"))[0]

    assert result.triggered is True
    assert result.watchlisted is False
    assert "metric_prevalence_gain" in result.change_reasons
    assert result.watch_reasons == ()
    assert result.watch_blockers == ()


def test_nonwatchlisted_cluster_exposes_structural_blocker() -> None:
    baseline = []
    current = [
        _signal("c1", "A", "demand", "backlog_strength"),
        _signal("c2", "B", "demand", "bookings_strength"),
    ]

    result = compare_windows(current, baseline, eligible_company_ids=("A", "B"))[0]

    assert result.watchlisted is False
    assert result.watch_reasons == ()
    assert "min_breadth" in result.watch_blockers
    assert "core_pair" in result.watch_blockers
    assert result.change_reasons
