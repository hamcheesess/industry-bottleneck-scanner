from datetime import datetime, timezone

from industry_bottleneck_scanner.candidate_adjudication import adjudicate_candidate, promote_candidate
from industry_bottleneck_scanner.candidate_retrieval import RetrievalCandidate
from industry_bottleneck_scanner.models import SourceDocument


def _doc() -> SourceDocument:
    return SourceDocument(
        document_id="call:TEST:2026Q2:turn:0001",
        company_id="issuer-test",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        text="Our output cannot keep up with incoming customer requirements.",
        speaker="CEO",
        speaker_title="Chief Executive Officer",
    )


def test_semantic_review_candidate_is_not_promoted() -> None:
    candidate = RetrievalCandidate(
        document_id=_doc().document_id,
        scanner="scarcity",
        metric="capacity_constraint",
        evidence_text=_doc().text,
        methods=("semantic_local",),
        score=0.82,
        review_tier="review",
    )

    result = adjudicate_candidate(candidate, _doc())
    assert result.status == "review"
    assert promote_candidate(result, _doc()) is None


def test_high_semantic_candidate_can_be_promoted_with_speaker_provenance() -> None:
    candidate = RetrievalCandidate(
        document_id=_doc().document_id,
        scanner="scarcity",
        metric="capacity_constraint",
        evidence_text=_doc().text,
        methods=("semantic_local",),
        score=0.93,
        review_tier="high",
    )

    result = adjudicate_candidate(candidate, _doc())
    signal = promote_candidate(result, _doc())

    assert result.status == "accepted"
    assert signal is not None
    assert signal.subject is None
    assert signal.speaker == "CEO"
    assert signal.speaker_title == "Chief Executive Officer"
    assert signal.extraction_method == "semantic_local"
    assert signal.confidence == 0.93


def test_candidate_with_foreign_evidence_is_rejected() -> None:
    candidate = RetrievalCandidate(
        document_id=_doc().document_id,
        scanner="demand",
        metric="backlog_strength",
        evidence_text="This sentence is not in the source.",
        methods=("keyword",),
        score=0.9,
        review_tier="high",
    )

    result = adjudicate_candidate(candidate, _doc())
    assert result.status == "rejected"
    assert result.reason == "evidence_not_in_document"
