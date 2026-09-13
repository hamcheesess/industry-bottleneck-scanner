from datetime import datetime, timezone

from industry_bottleneck_scanner.candidate_retrieval import RetrievalCandidate
from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.novel_language import cluster_pending_review_language
from industry_bottleneck_scanner.review_queue import ReviewRecord


class ControlledEncoder:
    def encode(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            if "outpacing" in lowered or "cannot keep up" in lowered or "running ahead" in lowered:
                vectors.append((1.0, 0.0))
            else:
                vectors.append((0.0, 1.0))
        return tuple(vectors)


def _record(review_id: str, company_id: str, text: str, *, status: str = "pending") -> ReviewRecord:
    return ReviewRecord(
        review_id=review_id,
        candidate=RetrievalCandidate(
            document_id=f"doc-{review_id}",
            scanner="scarcity",
            metric="capacity_constraint",
            evidence_text=text,
            methods=("semantic_local",),
            score=0.8,
            review_tier="review",
        ),
        company_id=company_id,
        ticker=company_id.upper(),
        document_type="earnings_call_turn",
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        classification=Classification(industry="Electrical Equipment"),
        source_url=None,
        speaker="CEO",
        speaker_title="CEO",
        source_section="qa",
        status=status,
    )


def test_repeated_semantic_only_language_surfaces_only_with_company_breadth() -> None:
    records = (
        _record("1", "a", "Customer requirements are outpacing available output."),
        _record("2", "b", "Our factories cannot keep up with incoming requirements."),
        _record("3", "c", "Demand is running ahead of available production."),
        _record("4", "d", "A completely unrelated sentence."),
    )

    clusters = cluster_pending_review_language(
        records,
        encoder=ControlledEncoder(),
        similarity_threshold=0.9,
        min_companies=3,
    )

    assert len(clusters) == 1
    assert clusters[0].metric == "capacity_constraint"
    assert clusters[0].company_ids == ("a", "b", "c")
    assert clusters[0].distinct_companies == 3


def test_resolved_review_records_do_not_seed_vocabulary_candidates() -> None:
    records = (
        _record("1", "a", "Customer requirements are outpacing available output."),
        _record("2", "b", "Our factories cannot keep up with incoming requirements.", status="accepted"),
        _record("3", "c", "Demand is running ahead of available production."),
    )

    clusters = cluster_pending_review_language(
        records,
        encoder=ControlledEncoder(),
        similarity_threshold=0.9,
        min_companies=3,
    )

    assert clusters == ()
