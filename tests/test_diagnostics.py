from datetime import datetime, timezone

from industry_bottleneck_scanner.diagnostics import summarize_signal_diagnostics
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _signal(
    signal_id: str,
    company_id: str,
    metric: str,
    *,
    section: str | None = "qa",
    extraction_method: str = "keyword",
    classified: bool = True,
) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner="scarcity",
        metric=metric,
        direction="strengthening",
        magnitude="unknown",
        company_id=company_id,
        ticker=company_id.upper(),
        classification=Classification(industry="Electrical Equipment") if classified else Classification(),
        subject=None,
        document_id=f"doc-{signal_id}",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="evidence",
        negated=False,
        resolved=False,
        extraction_method=extraction_method,
        confidence=0.8,
        source_section=section,
    )


def test_diagnostics_surface_concentration_section_and_classification_quality() -> None:
    signals = (
        _signal("1", "a", "capacity_constraint"),
        _signal("2", "a", "lead_time_pressure", section="prepared"),
        _signal("3", "b", "capacity_constraint", extraction_method="semantic_local"),
        _signal("4", "c", "supply_tightness", section=None, classified=False),
    )

    diagnostics = summarize_signal_diagnostics(signals)

    assert diagnostics.total_signals == 4
    assert diagnostics.active_strengthening == 4
    assert diagnostics.distinct_companies == 3
    assert diagnostics.distinct_metrics == 3
    assert diagnostics.qa_signals == 2
    assert diagnostics.prepared_signals == 1
    assert diagnostics.unknown_section_signals == 1
    assert diagnostics.unclassified_signals == 1
    assert diagnostics.semantic_only_signals == 1
    assert diagnostics.top_company_share == 0.5
    assert diagnostics.company_signal_counts[0] == ("a", 2)
