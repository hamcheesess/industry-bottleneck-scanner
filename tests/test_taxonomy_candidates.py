from industry_bottleneck_scanner.novel_language import NovelExpressionCluster
from industry_bottleneck_scanner.taxonomy_candidates import build_taxonomy_candidates


def _cluster(companies: int, similarity: float, metric: str = "capacity_constraint") -> NovelExpressionCluster:
    ids = tuple(f"issuer-{index}" for index in range(companies))
    return NovelExpressionCluster(
        scanner="scarcity",
        metric=metric,
        company_ids=ids,
        review_ids=tuple(f"review-{index}" for index in range(companies)),
        examples=("Customer requirements are outpacing available output.",),
        mean_similarity_to_centroid=similarity,
    )


def test_candidate_requires_independent_company_repetition() -> None:
    assert build_taxonomy_candidates((_cluster(2, 0.9),)) == ()


def test_high_priority_candidate_requires_breadth_and_similarity() -> None:
    result = build_taxonomy_candidates((_cluster(5, 0.85), _cluster(3, 0.75, "lead_time_pressure")))
    assert result[0].status == "high_priority_review"
    assert result[0].distinct_companies == 5
    assert result[1].status == "review"


def test_taxonomy_candidate_does_not_auto_promote() -> None:
    candidate = build_taxonomy_candidates((_cluster(5, 0.9),))[0]
    assert candidate.status == "high_priority_review"
    assert not hasattr(candidate, "accepted")
