from datetime import datetime, timezone

from industry_bottleneck_scanner.discovery_pipeline import scan_earnings_call
from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


def test_offline_transcript_pipeline_emits_signals_and_preserves_provenance() -> None:
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="POWL",
        fiscal_quarter="2026Q2",
        turns=(
            TranscriptTurn(
                speaker="CEO",
                title="Chief Executive Officer",
                text="Backlog reached a record level and capacity remains constrained.",
            ),
            TranscriptTurn(
                speaker="CEO",
                title="Chief Executive Officer",
                text="Pricing remains strong while we add capacity.",
            ),
        ),
    )

    result = scan_earnings_call(
        transcript,
        company_id="issuer-powl",
        published_at=datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc),
        classification=Classification(industry="Electrical Equipment"),
    )

    metrics = {signal.metric for signal in result.signals}
    assert "backlog_strength" in metrics
    assert "capacity_constraint" in metrics
    assert "pricing_power" in metrics
    assert result.review_candidates == ()
    assert result.rejected == ()
    assert result.document_count == 2
    assert all(signal.subject == "CEO" for signal in result.signals)
    assert all(signal.classification.industry == "Electrical Equipment" for signal in result.signals)
