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


def test_transcript_turns_preserve_speaker_provenance_and_sections() -> None:
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
    assert [document.source_section for document in documents] == ["prepared", "qa", "qa"]


def test_explicit_operator_marker_starts_qa_for_following_company_answers() -> None:
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="TEST",
        fiscal_quarter="2026Q2",
        turns=(
            TranscriptTurn(speaker="CEO", title="CEO", text="Prepared remarks."),
            TranscriptTurn(
                speaker="Operator",
                title="Operator",
                text="We will now begin the question-and-answer session.",
            ),
            TranscriptTurn(speaker="CEO", title="CEO", text="Pricing remains strong."),
        ),
    )
    documents = transcript_to_documents(
        transcript,
        company_id="issuer-test",
        published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
    )

    assert [document.source_section for document in documents] == ["prepared", "qa", "qa"]


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
    assert "capacity_expansion" not in metrics
    assert all(signal.document_type == "earnings_call_turn" for signal in signals)
    assert all("analyst" not in " ".join(filter(None, (signal.speaker, signal.speaker_title))).casefold() for signal in signals)
    assert {signal.extraction_method for signal in signals} <= {"keyword", "regex"}
    backlog = next(signal for signal in signals if signal.metric == "backlog_strength")
    assert backlog.extraction_method == "regex"
    assert "Backlog reached a record" in backlog.matched_phrase
    assert backlog.source_section == "prepared"
    pricing = next(signal for signal in signals if signal.metric == "pricing_power")
    assert pricing.source_section == "qa"


def test_analyst_hypothesis_does_not_become_company_scarcity_evidence() -> None:
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="TEST",
        fiscal_quarter="2019Q2",
        turns=(
            TranscriptTurn(speaker="Operator", title="Operator", text="Question-and-answer session."),
            TranscriptTurn(
                speaker="Research Analyst",
                title="Senior Equity Research Analyst",
                text="Was the weakness due to the long lead times you experienced?",
            ),
            TranscriptTurn(
                speaker="CEO",
                title="Chief Executive Officer",
                text="No, availability was normal and we did not see a supply constraint.",
            ),
        ),
    )

    signals = scan_transcript(
        transcript,
        company_id="issuer-test",
        published_at=datetime(2019, 7, 30, tzinfo=timezone.utc),
    )

    assert all(signal.metric != "lead_time_pressure" for signal in signals)
