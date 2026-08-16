from datetime import datetime, timezone

from industry_bottleneck_scanner.candidate_adjudication import adjudicate_candidate, promote_candidate
from industry_bottleneck_scanner.candidate_retrieval import RetrievalCandidate
from industry_bottleneck_scanner.models import SourceDocument


def _doc(text: str = "Our output cannot keep up with incoming customer requirements.") -> SourceDocument:
    return SourceDocument(
        document_id="call:TEST:2026Q2:turn:0001",
        company_id="issuer-test",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        text=text,
        speaker="CEO",
        speaker_title="Chief Executive Officer",
    )


def _candidate(*, document: SourceDocument, scanner: str, metric: str, methods=("semantic_local",), score=0.93, review_tier="high") -> RetrievalCandidate:
    return RetrievalCandidate(
        document_id=document.document_id,
        scanner=scanner,  # type: ignore[arg-type]
        metric=metric,
        evidence_text=document.text,
        methods=methods,
        score=score,
        review_tier=review_tier,
    )


def test_semantic_review_candidate_is_not_promoted() -> None:
    document = _doc()
    candidate = _candidate(
        document=document,
        scanner="scarcity",
        metric="capacity_constraint",
        score=0.82,
        review_tier="review",
    )

    result = adjudicate_candidate(candidate, document)
    assert result.status == "review"
    assert promote_candidate(result, document) is None


def test_high_semantic_candidate_can_be_promoted_with_speaker_provenance() -> None:
    document = _doc()
    candidate = _candidate(document=document, scanner="scarcity", metric="capacity_constraint")

    result = adjudicate_candidate(candidate, document)
    signal = promote_candidate(result, document)

    assert result.status == "accepted"
    assert signal is not None
    assert signal.subject is None
    assert signal.speaker == "CEO"
    assert signal.speaker_title == "Chief Executive Officer"
    assert signal.extraction_method == "semantic_local"
    assert signal.confidence == 0.93
    assert signal.direction == "strengthening"


def test_candidate_with_foreign_evidence_is_rejected() -> None:
    document = _doc()
    candidate = RetrievalCandidate(
        document_id=document.document_id,
        scanner="demand",
        metric="backlog_strength",
        evidence_text="This sentence is not in the source.",
        methods=("keyword",),
        score=0.9,
        review_tier="high",
    )

    result = adjudicate_candidate(candidate, document)
    assert result.status == "rejected"
    assert result.reason == "evidence_not_in_document"


def test_weakening_metric_is_not_promoted_as_strengthening() -> None:
    document = _doc("Backlog declined sequentially during the quarter.")
    candidate = _candidate(
        document=document,
        scanner="demand",
        metric="backlog_weakness",
        methods=("regex",),
        score=0.85,
    )

    signal = promote_candidate(adjudicate_candidate(candidate, document), document)

    assert signal is not None
    assert signal.direction == "weakening"
    assert signal.negated is False
    assert signal.resolved is False
    assert signal.comparison_basis == "prior_period"


def test_negated_strengthening_candidate_becomes_weakening_and_resolved() -> None:
    document = _doc("We are not capacity constrained today.")
    candidate = _candidate(
        document=document,
        scanner="scarcity",
        metric="capacity_constraint",
        methods=("regex",),
        score=0.9,
    )

    signal = promote_candidate(adjudicate_candidate(candidate, document), document)

    assert signal is not None
    assert signal.direction == "weakening"
    assert signal.negated is True
    assert signal.resolved is True
