from __future__ import annotations

from datetime import datetime

from .models import Classification
from .review_queue import FileReviewQueue
from .semantic_retrieval import LocalSemanticRetriever
from .source_scan import SourceScanResult, scan_source_documents
from .transcript_pipeline import transcript_to_documents
from .transcripts import EarningsCallTranscript

TranscriptScanResult = SourceScanResult


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
    return scan_source_documents(
        documents,
        semantic_retriever=semantic_retriever,
        review_queue=review_queue,
    )
