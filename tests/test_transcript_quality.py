from industry_bottleneck_scanner.transcript_quality import evaluate_transcript_quality
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def test_transcript_quality_reports_speaker_title_and_qa_coverage() -> None:
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="TEST",
        fiscal_quarter="2026Q2",
        turns=(
            TranscriptTurn(speaker="CEO", title="Chief Executive Officer", text="Prepared remarks."),
            TranscriptTurn(speaker="Operator", title=None, text="We will now begin the question-and-answer session."),
            TranscriptTurn(speaker="Analyst", title="Analyst", text="My question is about capacity."),
            TranscriptTurn(speaker="CEO", title="Chief Executive Officer", text="Capacity remains constrained."),
        ),
    )

    summary = evaluate_transcript_quality((transcript,))
    record = summary.records[0]

    assert summary.transcript_count == 1
    assert summary.total_turns == 4
    assert summary.average_turns == 4.0
    assert summary.speaker_label_rate == 1.0
    assert summary.title_label_rate == 0.75
    assert summary.transcripts_with_qa == 1
    assert summary.qa_detection_rate == 1.0
    assert record.prepared_turns == 1
    assert record.qa_turns == 3
