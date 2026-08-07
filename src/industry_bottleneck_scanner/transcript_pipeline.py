from __future__ import annotations

from datetime import datetime

from .models import AtomicSignal, Classification, SourceDocument
from .scanner import scan_document
from .transcripts import EarningsCallTranscript


def transcript_to_documents(
    transcript: EarningsCallTranscript,
    *,
    company_id: str,
    published_at: datetime,
    classification: Classification | None = None,
) -> tuple[SourceDocument, ...]:
    """Convert one normalized earnings call into turn-level scanner documents.

    ``published_at`` is required rather than inferred from the fiscal quarter. The fiscal
    quarter and actual call date are not interchangeable, and acceleration analysis must
    not be contaminated by an invented event date.
    """

    bucket = classification or Classification()
    documents: list[SourceDocument] = []

    for index, turn in enumerate(transcript.turns, start=1):
        text = turn.text.strip()
        if not text:
            continue
        document_id = (
            f"{transcript.provider}:{transcript.ticker}:"
            f"{transcript.fiscal_quarter}:turn:{index:04d}"
        )
        documents.append(
            SourceDocument(
                document_id=document_id,
                company_id=company_id,
                ticker=transcript.ticker,
                document_type="earnings_call_turn",
                published_at=published_at,
                text=text,
                classification=bucket,
                source_url=transcript.source_url,
                speaker=turn.speaker,
                speaker_title=turn.title,
            )
        )

    return tuple(documents)


def scan_transcript(
    transcript: EarningsCallTranscript,
    *,
    company_id: str,
    published_at: datetime,
    classification: Classification | None = None,
) -> tuple[AtomicSignal, ...]:
    """Run the deterministic Phase 1 scanner over each transcript turn."""

    signals: list[AtomicSignal] = []
    for document in transcript_to_documents(
        transcript,
        company_id=company_id,
        published_at=published_at,
        classification=classification,
    ):
        signals.extend(scan_document(document))
    return tuple(signals)
