from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .candidate_adjudication import AdjudicationResult, adjudicate_candidate, promote_candidate
from .candidate_retrieval import RetrievalCandidate, retrieve_candidates
from .models import AtomicSignal, SourceDocument
from .review_queue import FileReviewQueue, ReviewRecord
from .semantic_retrieval import LocalSemanticRetriever


@dataclass(frozen=True)
class SourceScanResult:
    signals: tuple[AtomicSignal, ...]
    review_candidates: tuple[RetrievalCandidate, ...]
    rejected: tuple[AdjudicationResult, ...]
    document_count: int
    candidate_count: int
    excluded_analyst_documents: int = 0
    queued_reviews: int = 0


def is_analyst_document(document: SourceDocument) -> bool:
    """Identify analyst-attributed transcript turns without affecting other sources."""

    haystack = " ".join(
        value for value in (document.speaker_title, document.speaker) if value
    ).casefold()
    return "analyst" in haystack


def scan_source_documents(
    documents: Iterable[SourceDocument],
    *,
    semantic_retriever: LocalSemanticRetriever | None = None,
    review_queue: FileReviewQueue | None = None,
) -> SourceScanResult:
    """Run the existing deterministic scanner over provider-normalized documents.

    The input may mix filings, releases, presentations, and transcript turns. Provider
    identity is carried only through document provenance. Analyst-attributed turns remain
    excluded before retrieval so their hypotheses cannot become issuer evidence.
    """

    items = tuple(documents)
    seen_document_ids: set[str] = set()
    for document in items:
        if document.document_id in seen_document_ids:
            raise ValueError(f"duplicate SourceDocument document_id: {document.document_id}")
        seen_document_ids.add(document.document_id)

    signals: list[AtomicSignal] = []
    review: list[RetrievalCandidate] = []
    review_records: list[ReviewRecord] = []
    rejected: list[AdjudicationResult] = []
    candidate_count = 0
    excluded_analyst_documents = 0

    for document in items:
        if is_analyst_document(document):
            excluded_analyst_documents += 1
            continue

        batch = retrieve_candidates(document, semantic_retriever=semantic_retriever)
        candidate_count += len(batch.candidates)
        for candidate in batch.candidates:
            decision = adjudicate_candidate(candidate, document)
            if decision.status == "review":
                review.append(candidate)
                if review_queue is not None:
                    review_records.append(ReviewRecord.from_candidate(candidate, document))
                continue
            if decision.status == "rejected":
                rejected.append(decision)
                continue
            signal = promote_candidate(decision, document)
            if signal is not None:
                signals.append(signal)

    queued_reviews = 0
    if review_queue is not None and review_records:
        queued_reviews = review_queue.enqueue(tuple(review_records))

    return SourceScanResult(
        signals=tuple(signals),
        review_candidates=tuple(review),
        rejected=tuple(rejected),
        document_count=len(items),
        candidate_count=candidate_count,
        excluded_analyst_documents=excluded_analyst_documents,
        queued_reviews=queued_reviews,
    )
