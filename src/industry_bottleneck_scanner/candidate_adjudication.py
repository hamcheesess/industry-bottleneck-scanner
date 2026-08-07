from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .candidate_retrieval import RetrievalCandidate
from .models import AtomicSignal, SourceDocument


@dataclass(frozen=True)
class AdjudicationResult:
    candidate: RetrievalCandidate
    status: str
    reason: str


def adjudicate_candidate(
    candidate: RetrievalCandidate,
    document: SourceDocument,
) -> AdjudicationResult:
    """Apply cheap deterministic guardrails before promoting a retrieval candidate.

    Lexical/regex-backed candidates are accepted because their evidence has already passed
    the scanner's explicit phrase/pattern checks. Semantic-only candidates remain review
    unless they are in the high tier. This function intentionally does not call an LLM.
    """

    if candidate.document_id != document.document_id:
        return AdjudicationResult(candidate, "rejected", "document_id_mismatch")
    if candidate.evidence_text not in document.text:
        return AdjudicationResult(candidate, "rejected", "evidence_not_in_document")
    if any(method in {"keyword", "regex"} for method in candidate.methods):
        return AdjudicationResult(candidate, "accepted", "deterministic_match")
    if candidate.review_tier == "high":
        return AdjudicationResult(candidate, "accepted", "high_similarity_semantic")
    return AdjudicationResult(candidate, "review", "semantic_only_requires_review")


def promote_candidate(
    result: AdjudicationResult,
    document: SourceDocument,
) -> AtomicSignal | None:
    if result.status != "accepted":
        return None

    candidate = result.candidate
    payload = "|".join(
        (
            document.document_id,
            candidate.scanner,
            candidate.metric,
            candidate.evidence_text,
            "+".join(candidate.methods),
        )
    ).encode("utf-8")
    signal_id = hashlib.sha256(payload).hexdigest()[:24]

    extraction_method = "+".join(candidate.methods)
    confidence = min(0.95, max(0.0, candidate.score))
    return AtomicSignal(
        signal_id=signal_id,
        scanner=candidate.scanner,
        metric=candidate.metric,
        direction="strengthening",
        magnitude="unknown",
        company_id=document.company_id,
        ticker=document.ticker,
        classification=document.classification,
        subject=document.speaker,
        document_id=document.document_id,
        document_type=document.document_type,
        published_at=document.published_at,
        source_url=document.source_url,
        evidence_text=candidate.evidence_text,
        negated=False,
        resolved=False,
        extraction_method=extraction_method,
        confidence=confidence,
        matched_phrase=None,
        comparison_basis="unspecified",
    )
