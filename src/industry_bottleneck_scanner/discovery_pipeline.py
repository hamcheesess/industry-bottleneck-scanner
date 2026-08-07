from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .candidate_adjudication import AdjudicationResult, adjudicate_candidate, promote_candidate
from .candidate_retrieval import RetrievalCandidate, retrieve_candidates
from .models import AtomicSignal, Classification
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


def scan_earnings_call(
    transcript: EarningsCallTranscript,
    *,
    company_id: str,
    published_at: datetime,
    classification: Classification = Classification(),
    semantic_retriever: LocalSemanticRetriever | None = None,
) -> TranscriptScanResult:
    """Run the local, no-LLM Phase-1 pipeline over one normalized earnings call."""

    documents = transcript_to_documents(
        transcript,
        company_id=company_id,
        published_at=published_at,
        classification=classification,
    )
    signals: list[AtomicSignal] = []
    review: list[RetrievalCandidate] = []
    rejected: list[AdjudicationResult] = []
    candidate_count = 0

    for document in documents:
        batch = retrieve_candidates(document, semantic_retriever=semantic_retriever)
        candidate_count += len(batch.candidates)
        for candidate in batch.candidates:
            decision = adjudicate_candidate(candidate, document)
            if decision.status == "review":
                review.append(candidate)
                continue
            if decision.status == "rejected":
                rejected.append(decision)
                continue
            signal = promote_candidate(decision, document)
            if signal is not None:
                signals.append(signal)

    return TranscriptScanResult(
        signals=tuple(signals),
        review_candidates=tuple(review),
        rejected=tuple(rejected),
        document_count=len(documents),
        candidate_count=candidate_count,
    )
