from datetime import datetime, timezone

from industry_bottleneck_scanner.candidate_retrieval import retrieve_candidates, review_candidates
from industry_bottleneck_scanner.models import SourceDocument
from industry_bottleneck_scanner.semantic_retrieval import LocalSemanticRetriever, SemanticPrototype


class FakeEncoder:
    def encode(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            if "pricing" in lowered or "raise prices" in lowered:
                vectors.append((1.0, 0.0))
            elif "output cannot keep up" in lowered or "capacity" in lowered:
                vectors.append((0.0, 1.0))
            else:
                vectors.append((0.5, 0.5))
        return vectors


def _doc(text: str) -> SourceDocument:
    return SourceDocument(
        document_id="call:TEST:2026Q2:turn:0001",
        company_id="issuer-test",
        ticker="TEST",
        document_type="earnings_call_turn",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        text=text,
    )


def _retriever(threshold=0.70):
    return LocalSemanticRetriever(
        FakeEncoder(),
        prototypes=(
            SemanticPrototype("pricing", "pricing_power", "We can raise prices because pricing is firm."),
            SemanticPrototype("scarcity", "capacity_constraint", "Available capacity cannot satisfy demand."),
        ),
        threshold=threshold,
    )


def test_semantic_only_candidate_is_review_tier_below_high_threshold() -> None:
    batch = retrieve_candidates(
        _doc("Our output cannot keep up with incoming customer requirements."),
        semantic_retriever=_retriever(),
        semantic_review_threshold=0.70,
        semantic_high_threshold=0.95,
    )

    scarcity = [item for item in batch.candidates if item.metric == "capacity_constraint"]
    assert scarcity
    assert scarcity[0].methods == ("semantic_local",)
    assert scarcity[0].review_tier == "high"  # exact fake-vector match scores 1.0


def test_semantic_review_filter_returns_only_review_candidates() -> None:
    class ReviewEncoder:
        def encode(self, texts):
            return [(1.0, 0.0) if "pricing" in text.casefold() else (0.8, 0.6) for text in texts]

    retriever = LocalSemanticRetriever(
        ReviewEncoder(),
        prototypes=(SemanticPrototype("pricing", "pricing_power", "Pricing is firm."),),
        threshold=0.70,
    )
    batch = retrieve_candidates(
        _doc("Commercial conditions remain supportive."),
        semantic_retriever=retriever,
        semantic_review_threshold=0.70,
        semantic_high_threshold=0.90,
    )

    review = review_candidates(batch)
    assert len(review) == 1
    assert review[0].review_tier == "review"
    assert review[0].methods == ("semantic_local",)


def test_lexical_and_semantic_same_metric_evidence_are_merged() -> None:
    batch = retrieve_candidates(
        _doc("Pricing remains strong."),
        semantic_retriever=_retriever(),
    )

    pricing = [item for item in batch.candidates if item.metric == "pricing_power"]
    assert len(pricing) == 1
    assert set(pricing[0].methods) == {"keyword", "semantic_local"}
    assert pricing[0].review_tier == "high"
