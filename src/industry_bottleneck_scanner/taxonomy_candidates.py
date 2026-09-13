from __future__ import annotations

from dataclasses import dataclass

from .novel_language import NovelExpressionCluster


@dataclass(frozen=True)
class TaxonomyCandidate:
    scanner: str
    metric: str
    distinct_companies: int
    mean_similarity: float
    examples: tuple[str, ...]
    status: str
    priority_score: float


def build_taxonomy_candidates(
    clusters: tuple[NovelExpressionCluster, ...],
    *,
    review_company_threshold: int = 3,
    high_company_threshold: int = 5,
) -> tuple[TaxonomyCandidate, ...]:
    """Rank repeated semantic-only language for human vocabulary maintenance.

    This never edits the production taxonomy. It only converts independently repeated
    review language into an auditable queue of candidate phrases for later acceptance.
    """

    if review_company_threshold < 2:
        raise ValueError("review_company_threshold must be at least 2")
    if high_company_threshold < review_company_threshold:
        raise ValueError("high_company_threshold must be >= review_company_threshold")

    candidates: list[TaxonomyCandidate] = []
    for cluster in clusters:
        companies = cluster.distinct_companies
        if companies < review_company_threshold:
            continue
        if companies >= high_company_threshold and cluster.mean_similarity_to_centroid >= 0.8:
            status = "high_priority_review"
        else:
            status = "review"
        priority = min(100.0, 12.0 * companies + 40.0 * cluster.mean_similarity_to_centroid)
        candidates.append(
            TaxonomyCandidate(
                scanner=cluster.scanner,
                metric=cluster.metric,
                distinct_companies=companies,
                mean_similarity=round(cluster.mean_similarity_to_centroid, 4),
                examples=cluster.examples,
                status=status,
                priority_score=round(priority, 2),
            )
        )

    return tuple(
        sorted(
            candidates,
            key=lambda item: (-item.priority_score, item.scanner, item.metric),
        )
    )
