from __future__ import annotations

from datetime import datetime

from .models import AtomicSignal, Classification, SourceDocument
from .scanner import scan_document
from .transcripts import EarningsCallTranscript, TranscriptTurn

_QA_MARKERS = (
    "question-and-answer session",
    "question and answer session",
    "q&a session",
    "q & a session",
    "open the line for questions",
    "open the call for questions",
    "take our first question",
    "first question comes from",
)


def _is_analyst(turn: TranscriptTurn) -> bool:
    haystack = " ".join(part for part in (turn.title, turn.speaker) if part).casefold()
    return "analyst" in haystack


def _document_is_analyst(document: SourceDocument) -> bool:
    haystack = " ".join(
        part for part in (document.speaker_title, document.speaker) if part
    ).casefold()
    return "analyst" in haystack


def _starts_qa(turn: TranscriptTurn) -> bool:
    text = turn.text.casefold()
    return _is_analyst(turn) or any(marker in text for marker in _QA_MARKERS)


def infer_turn_sections(transcript: EarningsCallTranscript) -> tuple[str, ...]:
    """Label each provider turn as prepared or Q&A without requiring event dates."""

    sections: list[str] = []
    in_qa = False
    for turn in transcript.turns:
        if not in_qa and _starts_qa(turn):
            in_qa = True
        sections.append("qa" if in_qa else "prepared")
    return tuple(sections)


def transcript_to_documents(
    transcript: EarningsCallTranscript,
    *,
    company_id: str,
    published_at: datetime,
    classification: Classification | None = None,
) -> tuple[SourceDocument, ...]:
    """Convert one normalized earnings call into turn-level scanner documents.

    The section boundary is inferred locally and conservatively. Once an explicit Q&A
    marker or analyst turn appears, subsequent turns are labeled ``qa``; earlier turns are
    labeled ``prepared``. Analyst turns are still retained as documents for transcript
    provenance and section diagnostics, but they are not treated as issuer evidence by
    ``scan_transcript``. The fiscal quarter is never used as a substitute for call time.
    """

    bucket = classification or Classification()
    documents: list[SourceDocument] = []
    sections = infer_turn_sections(transcript)

    for index, (turn, source_section) in enumerate(zip(transcript.turns, sections), start=1):
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
                source_section=source_section,
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
    """Run the deterministic Phase 1 scanner over issuer evidence in each transcript.

    Analyst questions are excluded from AtomicSignal production. They often contain a
    researcher's hypothesis (for example, asking whether long lead times caused a result)
    rather than a statement by the issuer. Counting those questions as company evidence can
    manufacture Demand/Scarcity prevalence and is therefore a provenance correctness bug,
    not a threshold-calibration issue. Management answers in the Q&A section remain eligible.
    """

    signals: list[AtomicSignal] = []
    for document in transcript_to_documents(
        transcript,
        company_id=company_id,
        published_at=published_at,
        classification=classification,
    ):
        if _document_is_analyst(document):
            continue
        signals.extend(scan_document(document))
    return tuple(signals)
