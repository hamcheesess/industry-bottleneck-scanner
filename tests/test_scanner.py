from datetime import datetime, timezone

from industry_bottleneck_scanner.models import Classification, SourceDocument
from industry_bottleneck_scanner.scanner import scan_document


def _doc(text: str) -> SourceDocument:
    return SourceDocument(
        document_id="doc-1",
        company_id="company-1",
        ticker="TEST",
        document_type="10-Q",
        published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        text=text,
        classification=Classification(
            sector="Industrials",
            industry="Electrical Equipment",
        ),
    )


def test_detects_multiple_logical_scanner_categories_from_one_document() -> None:
    signals = scan_document(
        _doc(
            "We reported record backlog. "
            "Lead times remain elevated and pricing remains strong. "
            "We also announced a capacity expansion."
        )
    )

    assert {signal.scanner for signal in signals} == {
        "capex",
        "demand",
        "scarcity",
        "pricing",
    }


def test_taxonomy_preserves_distinct_demand_and_scarcity_metrics() -> None:
    signals = scan_document(
        _doc(
            "We reported record backlog and customers are reserving capacity. "
            "Lead times remain elevated while capacity remains tight."
        )
    )

    metrics = {signal.metric for signal in signals}
    assert "backlog_strength" in metrics
    assert "forward_capacity_commitment" in metrics
    assert "lead_time_pressure" in metrics
    assert "capacity_constraint" in metrics


def test_capex_revision_is_distinct_from_capacity_expansion() -> None:
    signals = scan_document(
        _doc(
            "We raised capex guidance for the year. "
            "Construction of the capacity expansion has started."
        )
    )

    by_metric = {signal.metric: signal for signal in signals}
    assert by_metric["capex_revision_up"].comparison_basis == "prior_guidance_or_plan"
    assert by_metric["capacity_expansion"].comparison_basis == "unspecified"


def test_forward_capacity_commitment_preserves_comparison_basis() -> None:
    signals = scan_document(
        _doc("Customers are reserving capacity under a multi-year agreement.")
    )

    demand = [signal for signal in signals if signal.metric == "forward_capacity_commitment"]
    assert demand
    assert all(signal.comparison_basis == "forward_commitment" for signal in demand)
    assert all(signal.matched_phrase for signal in demand)


def test_resolved_constraint_does_not_remain_strengthening() -> None:
    signals = scan_document(
        _doc("Lead times remain elevated, but conditions have normalized and supply improved.")
    )

    scarcity = [signal for signal in signals if signal.scanner == "scarcity"]
    assert len(scarcity) == 1
    assert scarcity[0].resolved is True
    assert scarcity[0].direction == "weakening"


def test_explicit_weakening_pattern_is_not_mislabeled_as_resolution() -> None:
    signals = scan_document(_doc("Pricing declined during the quarter."))

    pricing = [signal for signal in signals if signal.metric == "pricing_weakness"]
    assert len(pricing) == 1
    assert pricing[0].direction == "weakening"
    assert pricing[0].resolved is False
    assert pricing[0].comparison_basis == "prior_period"


def test_signal_ids_are_deterministic() -> None:
    document = _doc("We reported record backlog.")
    first = scan_document(document)
    second = scan_document(document)

    assert [signal.signal_id for signal in first] == [signal.signal_id for signal in second]
