from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .review_queue import ReviewRecord
from .semantic_retrieval import EmbeddingEncoder


@dataclass(frozen=True)
class NovelExpressionCluster:
    scanner: str
    metric: str
    company_ids: tuple[str, ...]
    review_ids: tuple[str, ...]
    examples: tuple[str, ...]
    mean_similarity_to_centroid: float

    @property
    def distinct_companies(self) -> int:
        return len(self.company_ids)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _centroid(vectors: Sequence[Sequence[float]]) -> tuple[float, ...]:
    if not vectors:
        raise ValueError("cannot compute centroid of empty vectors")
    width = len(vectors[0])
    if any(len(vector) != width for vector in vectors):
        raise ValueError("embedding dimensions must match")
    values = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(width)]
    norm = math.sqrt(sum(value * value for value in values))
    if norm:
        values = [value / norm for value in values]
    return tuple(values)


def cluster_pending_review_language(
    records: Sequence[ReviewRecord],
    *,
    encoder: EmbeddingEncoder,
    similarity_threshold: float = 0.72,
    min_companies: int = 3,
    max_examples: int = 5,
) -> tuple[NovelExpressionCluster, ...]:
    """Find repeated semantic-only language across independent issuers.

    Only pending review records participate. Candidates are grouped within the same
    scanner/metric and greedily assigned to a centroid when their local-embedding cosine
    similarity clears the threshold. Results below ``min_companies`` are discarded.

    These clusters are vocabulary-development candidates only: they never create an
    AtomicSignal or alter production vocabulary automatically.
    """

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1")
    if min_companies < 2:
        raise ValueError("min_companies must be at least 2")
    if max_examples < 1:
        raise ValueError("max_examples must be at least 1")

    pending = [record for record in records if record.status == "pending"]
    if not pending:
        return ()

    grouped: dict[tuple[str, str], list[ReviewRecord]] = {}
    for record in pending:
        key = (record.candidate.scanner, record.candidate.metric)
        grouped.setdefault(key, []).append(record)

    results: list[NovelExpressionCluster] = []
    for (scanner, metric), items in sorted(grouped.items()):
        texts = [item.candidate.evidence_text for item in items]
        vectors = [tuple(vector) for vector in encoder.encode(texts)]
        if len(vectors) != len(items):
            raise ValueError("encoder returned the wrong number of vectors")

        clusters: list[tuple[list[ReviewRecord], list[tuple[float, ...]]]] = []
        for record, vector in zip(items, vectors):
            best_index: int | None = None
            best_similarity = -1.0
            for index, (_, cluster_vectors) in enumerate(clusters):
                similarity = _cosine(vector, _centroid(cluster_vectors))
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_index = index
                    best_similarity = similarity
            if best_index is None:
                clusters.append(([record], [vector]))
            else:
                clusters[best_index][0].append(record)
                clusters[best_index][1].append(vector)

        for cluster_records, cluster_vectors in clusters:
            company_ids = tuple(sorted({record.company_id for record in cluster_records}))
            if len(company_ids) < min_companies:
                continue
            center = _centroid(cluster_vectors)
            mean_similarity = sum(_cosine(vector, center) for vector in cluster_vectors) / len(cluster_vectors)
            ordered_records = sorted(cluster_records, key=lambda record: (record.company_id, record.review_id))
            examples = tuple(
                dict.fromkeys(record.candidate.evidence_text for record in ordered_records)
            )[:max_examples]
            results.append(
                NovelExpressionCluster(
                    scanner=scanner,
                    metric=metric,
                    company_ids=company_ids,
                    review_ids=tuple(record.review_id for record in ordered_records),
                    examples=examples,
                    mean_similarity_to_centroid=mean_similarity,
                )
            )

    return tuple(
        sorted(
            results,
            key=lambda item: (
                -item.distinct_companies,
                -item.mean_similarity_to_centroid,
                item.scanner,
                item.metric,
            ),
        )
    )
