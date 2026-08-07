from datetime import datetime, timezone

from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.transcript_pipeline import (
    scan_transcript,
    transcript_to_documents,
)
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def _transcript() -> EarningsCallTranscript:
    return EarningsCallTranscript(
        provider="fixture",
        ticker="POWL",
        fiscal_quarter="2026Q2",
        source_url="https://example.test/powl",
        turns=(
            TranscriptTurn(
                speaker="CEO",
                title="Chief Executive Officer",
                text="Backlog reached a record level and capacity remains constrained.",
            ),
            TranscriptTurn(
                speaker="Analyst",
                title="Analyst",
                text="How long will the expansion project take?",
            ),
            TranscriptTurn(
                speaker="CEO",
                title="Chief Executive Officer",
                text="Pricing remains strong while we add capacity.",
            ),
        ),
    )


def test_transcript_turns_preserve_speaker_provenance() -> None:
    published_at = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    documents = transcript_to_documents(
        _transcript(),
        company_id="issuer-powl",
        published_at=published_at,
        classification=Classification(sector="Industrials", industry="Electrical Equipment"),
    )

    assert len(documents) == 3
    assert documents[0].document_id.endswith("turn:0001")
    assert documents[0].speaker == "CEO"
    assert documents[0].speaker_title == "Chief Executive Officer"
    assert documents[0].published_at == published_at
    assert documents[0].classification.industry == "Electrical Equipment"


def test_scan_transcript_emits_signals_without_sending_full_call_to_an_llm() -> None:
    signals = scan_transcript(
        _transcript(),
        company_id="issuer-powl",
        published_at=datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc),
        classification=Classification(industry="Electrical Equipment"),
    )

    metrics = {signal.metric for signal in signals}
    assert "backlog_strength" in metrics
    assert "capacity_constraint" in metrics
    assert "pricing_power" in metrics
    assert all(signal.document_type == "earnings_call_turn" for signal in signals)
    assert all(signal.extraction_method == "keyword" for signal in signals)
