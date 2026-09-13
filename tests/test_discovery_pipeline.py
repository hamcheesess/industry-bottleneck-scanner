from datetime import datetime, timezone

from industry_bottleneck_scanner.discovery_pipeline import scan_earnings_call
from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.review_queue import FileReviewQueue
from industry_bottleneck_scanner.semantic_retrieval import SemanticCandidate
from industry_bottleneck_scanner.transcripts import EarningsCallTranscript, TranscriptTurn


class ReviewOnlyRetriever:
    def retrieve(self, document):
        return (
            SemanticCandidate(
                document_id=document.document_id,
                scanner="scarcity",
                metric="capacity_constraint",
                evidence_text=document.text,
                similarity=0.80,
            ),
        )


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
    assert all(signal.subject is None for signal in result.signals)
    assert all(signal.speaker == "CEO" for signal in result.signals)
    assert all(signal.speaker_title == "Chief Executive Officer" for signal in result.signals)
    assert all(signal.classification.industry == "Electrical Equipment" for signal in result.signals)


def test_review_tier_candidates_are_persisted_without_raw_full_call(tmp_path) -> None:
    evidence = "Customer requirements are outpacing available output."
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="TEST",
        fiscal_quarter="2026Q2",
        turns=(TranscriptTurn(speaker="CEO", title="CEO", text=evidence),),
    )
    queue = FileReviewQueue(tmp_path / "review.json")

    result = scan_earnings_call(
        transcript,
        company_id="issuer-test",
        published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
        classification=Classification(industry="Electrical Equipment"),
        semantic_retriever=ReviewOnlyRetriever(),
        review_queue=queue,
    )

    assert result.signals == ()
    assert len(result.review_candidates) == 1
    assert result.queued_reviews == 1
    pending = queue.pending()
    assert len(pending) == 1
    assert pending[0].candidate.evidence_text == evidence
    assert pending[0].company_id == "issuer-test"


def test_analyst_questions_do_not_become_production_signals_but_management_answers_do() -> None:
    transcript = EarningsCallTranscript(
        provider="fixture",
        ticker="TEST",
        fiscal_quarter="2019Q2",
        turns=(
            TranscriptTurn(
                speaker="Analyst Name",
                title="Research Analyst",
                text="Was the weakness caused by long lead times?",
            ),
            TranscriptTurn(
                speaker="CEO Name",
                title="Chief Executive Officer",
                text="Backlog remains strong and we are adding capacity.",
            ),
        ),
    )

    result = scan_earnings_call(
        transcript,
        company_id="issuer-test",
        published_at=datetime(2019, 7, 30, tzinfo=timezone.utc),
        classification=Classification(sector="Information Technology"),
    )

    metrics = {signal.metric for signal in result.signals}
    assert "lead_time_pressure" not in metrics
    assert "backlog_strength" in metrics
    assert "capacity_expansion" in metrics
    assert all("analyst" not in " ".join(filter(None, (signal.speaker_title, signal.speaker))).casefold() for signal in result.signals)
    assert result.document_count == 2
