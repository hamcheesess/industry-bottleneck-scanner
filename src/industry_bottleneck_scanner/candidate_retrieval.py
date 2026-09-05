from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import ScannerCategory, SourceDocument
from .scanner import scan_document
from .semantic_retrieval import LocalSemanticRetriever, SemanticCandidate


@dataclass(frozen=True)
class RetrievalCandidate:
    document_id: str
    scanner: ScannerCategory
    metric: str
    evidence_text: str
    methods: tuple[str, ...]
    score: float
    review_tier: str


@dataclass(frozen=True)
class RetrievalBatch:
    candidates: tuple[RetrievalCandidate, ...]
    lexical_count: int
    semantic_count: int
    merged_count: int


def _key(document_id: str, scanner: str, metric: str, evidence_text: str) -> tuple[str, str, str, str]:
    return (document_id, scanner, metric, " ".join(evidence_text.casefold().split()))


def retrieve_candidates(
    document: SourceDocument,
    *,
    semantic_retriever: LocalSemanticRetriever | None = None,
    semantic_review_threshold: float = 0.72,
    semantic_high_threshold: float = 0.88,
) -> RetrievalBatch:
    """Combine deterministic scanner hits with optional local semantic retrieval.

    Lexical/regex hits are treated as auditable high-confidence candidates. Semantic-only
    hits are never promoted directly to an AtomicSignal here; they are review candidates.
    When lexical and semantic retrieval hit the same evidence/metric, the records are merged.
    """

    if not 0.0 <= semantic_review_threshold <= semantic_high_threshold <= 1.0:
        raise ValueError("semantic thresholds must satisfy 0 <= review <= high <= 1")

    merged: dict[tuple[str, str, str, str], RetrievalCandidate] = {}
    lexical_signals = scan_document(document)

    for signal in lexical_signals:
        key = _key(signal.document_id, signal.scanner, signal.metric, signal.evidence_text)
        merged[key] = RetrievalCandidate(
            document_id=signal.document_id,
            scanner=signal.scanner,
            metric=signal.metric,
            evidence_text=signal.evidence_text,
            methods=(signal.extraction_method,),
            score=signal.confidence,
            review_tier="high",
        )

    semantic_candidates: tuple[SemanticCandidate, ...] = ()
    if semantic_retriever is not None:
        semantic_candidates = semantic_retriever.retrieve(document)

    for candidate in semantic_candidates:
        if candidate.similarity < semantic_review_threshold:
            continue
        key = _key(
            candidate.document_id,
            candidate.scanner,
            candidate.metric,
            candidate.evidence_text,
        )
        previous = merged.get(key)
        if previous is not None:
            methods = tuple(dict.fromkeys((*previous.methods, candidate.extraction_method)))
            merged[key] = RetrievalCandidate(
                document_id=previous.document_id,
                scanner=previous.scanner,
                metric=previous.metric,
                evidence_text=previous.evidence_text,
                methods=methods,
                score=max(previous.score, candidate.similarity),
                review_tier="high",
            )
            continue

        tier = "high" if candidate.similarity >= semantic_high_threshold else "review"
        merged[key] = RetrievalCandidate(
            document_id=candidate.document_id,
            scanner=candidate.scanner,
            metric=candidate.metric,
            evidence_text=candidate.evidence_text,
            methods=(candidate.extraction_method,),
            score=candidate.similarity,
            review_tier=tier,
        )

    return RetrievalBatch(
        candidates=tuple(merged.values()),
        lexical_count=len(lexical_signals),
        semantic_count=len(semantic_candidates),
        merged_count=len(merged),
    )


def review_candidates(batch: RetrievalBatch) -> tuple[RetrievalCandidate, ...]:
    return tuple(candidate for candidate in batch.candidates if candidate.review_tier == "review")
