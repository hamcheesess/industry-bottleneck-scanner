from datetime import datetime, timezone

from industry_bottleneck_scanner.candidate_retrieval import RetrievalCandidate
from industry_bottleneck_scanner.models import Classification, SourceDocument
from industry_bottleneck_scanner.review_queue import FileReviewQueue, ReviewRecord


def _record() -> ReviewRecord:
    document = SourceDocument(
        document_id="doc-1",
        company_id="issuer-1",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        text="Customer requirements are outpacing available output.",
        classification=Classification(industry="Electrical Equipment"),
        speaker="CEO",
        speaker_title="Chief Executive Officer",
    )
    candidate = RetrievalCandidate(
        document_id=document.document_id,
        scanner="scarcity",
        metric="capacity_constraint",
        evidence_text=document.text,
        methods=("semantic_local",),
        score=0.81,
        review_tier="review",
    )
    return ReviewRecord.from_candidate(candidate, document)


def test_review_queue_deduplicates_and_persists(tmp_path) -> None:
    queue = FileReviewQueue(tmp_path / "review.json")
    record = _record()

    assert queue.enqueue((record,)) == 1
    assert queue.enqueue((record,)) == 0
    assert queue.pending()[0].review_id == record.review_id
    assert queue.pending()[0].speaker == "CEO"


def test_accepting_review_promotes_atomic_signal(tmp_path) -> None:
    queue = FileReviewQueue(tmp_path / "review.json")
    record = _record()
    queue.enqueue((record,))

    signal = queue.resolve(record.review_id, accepted=True, reason="manual_validation")

    assert signal is not None
    assert signal.metric == "capacity_constraint"
    assert signal.company_id == "issuer-1"
    assert signal.subject is None
    assert signal.speaker == "CEO"
    assert signal.speaker_title == "Chief Executive Officer"
    assert queue.pending() == ()


def test_rejecting_review_does_not_promote_signal(tmp_path) -> None:
    queue = FileReviewQueue(tmp_path / "review.json")
    record = _record()
    queue.enqueue((record,))

    assert queue.resolve(record.review_id, accepted=False, reason="false_positive") is None
    assert queue.pending() == ()
