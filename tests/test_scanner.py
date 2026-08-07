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


def test_resolved_constraint_does_not_remain_strengthening() -> None:
    signals = scan_document(
        _doc("Lead times remain elevated, but conditions have normalized and improved.")
    )

    scarcity = [signal for signal in signals if signal.scanner == "scarcity"]
    assert len(scarcity) == 1
    assert scarcity[0].resolved is True
    assert scarcity[0].direction == "weakening"


def test_signal_ids_are_deterministic() -> None:
    document = _doc("We reported record backlog.")
    first = scan_document(document)
    second = scan_document(document)

    assert [signal.signal_id for signal in first] == [signal.signal_id for signal in second]
