from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .candidate_adjudication import AdjudicationResult, adjudicate_candidate, promote_candidate
from .candidate_retrieval import RetrievalCandidate, retrieve_candidates
from .models import AtomicSignal, Classification, SourceDocument
from .review_queue import FileReviewQueue, ReviewRecord
from .semantic_retrieval import LocalSemanticRetriever
from .transcript_pipeline import transcript_to_documents
from .transcripts import EarningsCallTranscript


@dataclass(frozen=True)
class TranscriptScanResult:
    signals: tuple[AtomicSignal, ...]
    review_candidates: tuple[RetrievalCandidate, ...]
    rejected: tuple[AdjudicationResult, ...]
    document_count: int
    candidate_count: int
    queued_reviews: int = 0


def _is_analyst_document(document: SourceDocument) -> bool:
    """Return true when a transcript turn is attributable to an analyst.

    Analyst questions remain represented in the turn-level document stream so Q&A
    section provenance stays intact, but their hypotheses must not become issuer-origin
    AtomicSignals. Management answers in the same Q&A section remain eligible.
    """

    haystack = " ".join(
        value for value in (document.speaker_title, document.speaker) if value
    ).casefold()
    return "analyst" in haystack


def scan_earnings_call(
    transcript: EarningsCallTranscript,
    *,
    company_id: str,
    published_at: datetime,
    classification: Classification = Classification(),
    semantic_retriever: LocalSemanticRetriever | None = None,
    review_queue: FileReviewQueue | None = None,
) -> TranscriptScanResult:
    """Run the local, no-LLM Phase-1 pipeline over one normalized earnings call.

    Review-tier semantic candidates remain separate from accepted AtomicSignals. When a
    review queue is supplied they are persisted with the minimum source provenance needed
    for later reprocessing; no raw full-call transcript is written to the review queue.

    Analyst turns are retained in the document count and sectioning provenance but are
    excluded before candidate retrieval/adjudication so analyst hypotheses cannot be
    promoted as company evidence. Management Q&A answers remain eligible.
    """

    documents = transcript_to_documents(
        transcript,
        company_id=company_id,
        published_at=published_at,
        classification=classification,
    )
    signals: list[AtomicSignal] = []
    review: list[RetrievalCandidate] = []
    review_records: list[ReviewRecord] = []
    rejected: list[AdjudicationResult] = []
    candidate_count = 0

    for document in documents:
        if _is_analyst_document(document):
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

    return TranscriptScanResult(
        signals=tuple(signals),
        review_candidates=tuple(review),
        rejected=tuple(rejected),
        document_count=len(documents),
        candidate_count=candidate_count,
        queued_reviews=queued_reviews,
    )
