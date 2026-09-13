from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from .models import ScannerCategory, SourceDocument


class EmbeddingEncoder(Protocol):
    """Local embedding boundary.

    Implementations may use a local sentence-embedding model, but this protocol does not
    require network access or any paid API.
    """

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...


@dataclass(frozen=True)
class SemanticPrototype:
    scanner: ScannerCategory
    metric: str
    text: str


@dataclass(frozen=True)
class SemanticCandidate:
    document_id: str
    scanner: ScannerCategory
    metric: str
    evidence_text: str
    similarity: float
    extraction_method: str = "semantic_local"


DEFAULT_PROTOTYPES: tuple[SemanticPrototype, ...] = (
    SemanticPrototype(
        scanner="demand",
        metric="backlog_strength",
        text="Customer orders are accumulating faster and the order backlog is at unusually high levels.",
    ),
    SemanticPrototype(
        scanner="demand",
        metric="forward_capacity_commitment",
        text="Customers are reserving future production capacity under long-term commitments.",
    ),
    SemanticPrototype(
        scanner="scarcity",
        metric="capacity_constraint",
        text="Available production capacity is insufficient to satisfy current customer demand.",
    ),
    SemanticPrototype(
        scanner="scarcity",
        metric="lead_time_pressure",
        text="Customers face unusually long delivery lead times because supply cannot respond quickly.",
    ),
    SemanticPrototype(
        scanner="capex",
        metric="capacity_expansion",
        text="The company is adding manufacturing capacity through new facilities or production lines.",
    ),
    SemanticPrototype(
        scanner="pricing",
        metric="pricing_power",
        text="Tight supply and strong demand are allowing the company to sustain or raise prices.",
    ),
)


def _sentences(text: str) -> tuple[str, ...]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return tuple(chunk.strip() for chunk in chunks if chunk.strip())


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


class LocalSemanticRetriever:
    def __init__(
        self,
        encoder: EmbeddingEncoder,
        *,
        prototypes: tuple[SemanticPrototype, ...] = DEFAULT_PROTOTYPES,
        threshold: float = 0.72,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not prototypes:
            raise ValueError("at least one semantic prototype is required")
        self.encoder = encoder
        self.prototypes = prototypes
        self.threshold = threshold
        encoded = encoder.encode([prototype.text for prototype in prototypes])
        if len(encoded) != len(prototypes):
            raise ValueError("encoder returned the wrong number of prototype vectors")
        self._prototype_vectors = tuple(tuple(vector) for vector in encoded)

    def retrieve(self, document: SourceDocument) -> tuple[SemanticCandidate, ...]:
        sentences = _sentences(document.text)
        if not sentences:
            return ()
        encoded_sentences = self.encoder.encode(sentences)
        if len(encoded_sentences) != len(sentences):
            raise ValueError("encoder returned the wrong number of sentence vectors")

        candidates: list[SemanticCandidate] = []
        for sentence, vector in zip(sentences, encoded_sentences):
            best_by_metric: dict[tuple[str, str], tuple[SemanticPrototype, float]] = {}
            for prototype, prototype_vector in zip(self.prototypes, self._prototype_vectors):
                similarity = _cosine(vector, prototype_vector)
                key = (prototype.scanner, prototype.metric)
                previous = best_by_metric.get(key)
                if previous is None or similarity > previous[1]:
                    best_by_metric[key] = (prototype, similarity)

            for prototype, similarity in best_by_metric.values():
                if similarity < self.threshold:
                    continue
                candidates.append(
                    SemanticCandidate(
                        document_id=document.document_id,
                        scanner=prototype.scanner,
                        metric=prototype.metric,
                        evidence_text=sentence,
                        similarity=similarity,
                    )
                )

        return tuple(candidates)
