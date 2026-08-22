from datetime import datetime, timedelta, timezone

import pytest

from industry_bottleneck_scanner.disclosure_documents import (
    DisclosureSection,
    PublicDisclosure,
    disclosure_to_documents,
    normalize_disclosures,
)
from industry_bottleneck_scanner.models import Classification, SourceDocument
from industry_bottleneck_scanner.source_scan import scan_source_documents


PUBLISHED = datetime(2026, 8, 1, 20, 0, tzinfo=timezone.utc)


def disclosure() -> PublicDisclosure:
    return PublicDisclosure(
        provider="sec_edgar",
        provider_document_id="0000123456-26-000001",
        company_id="cik-0000123456",
        ticker="TEST",
        document_type="sec_8k_exhibit",
        published_at=PUBLISHED,
        retrieved_at=PUBLISHED + timedelta(hours=1),
        source_url="https://www.sec.gov/Archives/example.htm",
        classification=Classification(industry="Electrical Equipment"),
        sections=(
            DisclosureSection(
                section_id="earnings-release",
                source_section="results",
                text="Backlog reached a record level and capacity remains constrained.",
            ),
            DisclosureSection(
                section_id="outlook",
                text="Pricing remains strong while we add capacity.",
            ),
        ),
    )


def test_normalizes_public_disclosure_to_stable_source_documents() -> None:
    first = disclosure_to_documents(disclosure(), as_of=PUBLISHED + timedelta(days=1))
    second = disclosure_to_documents(disclosure(), as_of=PUBLISHED + timedelta(days=1))

    assert first == second
    assert len(first) == 2
    assert first[0].provider == "sec_edgar"
    assert first[0].source_section == "results"
    assert first[0].retrieved_at == PUBLISHED + timedelta(hours=1)
    assert len(first[0].content_fingerprint or "") == 64
    assert first[0].document_id != first[1].document_id


def test_future_disclosure_is_rejected_by_strict_as_of() -> None:
    with pytest.raises(ValueError, match="later than as_of"):
        disclosure_to_documents(disclosure(), as_of=PUBLISHED - timedelta(seconds=1))


def test_duplicate_normalized_disclosure_is_rejected() -> None:
    item = disclosure()
    with pytest.raises(ValueError, match="duplicate normalized SourceDocument"):
        normalize_disclosures((item, item), as_of=PUBLISHED + timedelta(days=1))


def test_generic_source_scan_reuses_scanner_and_excludes_analyst_turns() -> None:
    public_documents = disclosure_to_documents(
        disclosure(),
        as_of=PUBLISHED + timedelta(days=1),
    )
    analyst = SourceDocument(
        document_id="analyst-turn",
        company_id="cik-0000123456",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=PUBLISHED,
        text="Are long lead times creating a capacity constraint?",
        classification=Classification(industry="Electrical Equipment"),
        speaker="Analyst Name",
        speaker_title="Research Analyst",
        source_section="qa",
    )

    result = scan_source_documents((*public_documents, analyst))

    metrics = {signal.metric for signal in result.signals}
    assert "backlog_strength" in metrics
    assert "capacity_constraint" in metrics
    assert "pricing_power" in metrics
    assert "lead_time_pressure" not in metrics
    assert result.document_count == 3
    assert result.excluded_analyst_documents == 1


def test_generic_source_scan_rejects_duplicate_document_ids() -> None:
    item = disclosure_to_documents(disclosure())[0]
    with pytest.raises(ValueError, match="duplicate SourceDocument"):
        scan_source_documents((item, item))
