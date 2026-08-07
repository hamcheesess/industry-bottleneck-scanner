from datetime import datetime, timezone

from industry_bottleneck_scanner.aggregation import compare_windows, summarize
from industry_bottleneck_scanner.models import AtomicSignal, Classification


def _signal(
    signal_id: str,
    company_id: str,
    scanner: str,
    *,
    industry: str = "Electrical Equipment",
    confidence: float = 0.8,
) -> AtomicSignal:
    return AtomicSignal(
        signal_id=signal_id,
        scanner=scanner,  # type: ignore[arg-type]
        metric="metric",
        direction="strengthening",
        magnitude="unknown",
        company_id=company_id,
        ticker=None,
        classification=Classification(industry=industry),
        subject=None,
        document_id=f"doc-{signal_id}",
        document_type="10-Q",
        published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        source_url=None,
        evidence_text="evidence",
        negated=False,
        resolved=False,
        extraction_method="rule",
        confidence=confidence,
    )


def test_summary_prioritizes_distinct_company_breadth() -> None:
    signals = [
        _signal("1", "a", "scarcity"),
        _signal("2", "a", "scarcity"),
        _signal("3", "b", "pricing"),
    ]

    summary = summarize(signals)[0]
    assert summary.distinct_companies == 2
    assert summary.distinct_documents == 3
    assert set(summary.active_categories) == {"scarcity", "pricing"}


def test_acceleration_trigger_requires_breadth_growth_and_category_breadth() -> None:
    baseline = [_signal("b1", "a", "scarcity")]
    current = [
        _signal("c1", "a", "scarcity"),
        _signal("c2", "b", "scarcity"),
        _signal("c3", "c", "pricing"),
    ]

    result = compare_windows(current, baseline)[0]
    assert result.breadth_current == 3
    assert result.breadth_baseline == 1
    assert result.breadth_change == 2
    assert result.category_breadth == 2
    assert result.triggered is True
