from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import AtomicSignal, ComparisonBasis, SourceDocument
from .vocabulary import DEFAULT_PATTERNS, SignalPattern

_NEGATION_MARKERS = (
    "no longer",
    "not constrained",
    "not capacity constrained",
    "not supply constrained",
    "isn't constrained",
    "is not constrained",
)

_RESOLUTION_MARKERS = (
    "normalized",
    "normalised",
    "conditions improved",
    "constraints eased",
    "constraint eased",
    "supply improved",
    "availability improved",
)

_PRIOR_PERIOD_MARKERS = (
    "increased",
    "grew",
    "growth",
    "decreased",
    "declined",
    "contracted",
    "year over year",
    "year-over-year",
    "sequentially",
)


@dataclass(frozen=True)
class PatternMatch:
    text: str
    method: str


def _sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _signal_id(document_id: str, scanner: str, metric: str, evidence: str) -> str:
    payload = "|".join((document_id, scanner, metric, evidence)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _match_pattern(sentence: str, pattern: SignalPattern) -> PatternMatch | None:
    lowered = sentence.casefold()
    for phrase in pattern.phrases:
        if phrase.casefold() in lowered:
            return PatternMatch(text=phrase, method="keyword")
    for expression in pattern.regex_patterns:
        match = re.search(expression, sentence, flags=re.IGNORECASE)
        if match is not None:
            return PatternMatch(text=match.group(0), method="regex")
    return None


def _is_negated(sentence: str) -> bool:
    lowered = sentence.casefold()
    return any(marker in lowered for marker in _NEGATION_MARKERS)


def _is_resolved(sentence: str, pattern: SignalPattern) -> bool:
    if pattern.direction != "strengthening":
        return False
    lowered = sentence.casefold()
    return _is_negated(sentence) or any(marker in lowered for marker in _RESOLUTION_MARKERS)


def _comparison_basis(sentence: str, pattern: SignalPattern) -> ComparisonBasis:
    metric = pattern.metric
    lowered = sentence.casefold()

    if metric.startswith("capex_revision_"):
        return "prior_guidance_or_plan"
    if metric == "book_to_bill_above_one":
        return "threshold"
    if metric in {"forward_capacity_commitment", "sold_out_capacity"}:
        return "forward_commitment"
    if any(marker in lowered for marker in _PRIOR_PERIOD_MARKERS):
        return "prior_period"
    return "unspecified"


def scan_document(
    document: SourceDocument,
    *,
    patterns: tuple[SignalPattern, ...] = DEFAULT_PATTERNS,
) -> list[AtomicSignal]:
    """Run deterministic phrase and regex matching over one source document."""

    signals: list[AtomicSignal] = []
    for sentence in _sentences(document.text):
        for pattern in patterns:
            match = _match_pattern(sentence, pattern)
            if match is None:
                continue

            negated = _is_negated(sentence)
            resolved = _is_resolved(sentence, pattern)
            direction = "weakening" if resolved else pattern.direction
            confidence = max(0.0, pattern.base_confidence - (0.2 if resolved else 0.0))

            signals.append(
                AtomicSignal(
                    signal_id=_signal_id(document.document_id, pattern.scanner, pattern.metric, sentence),
                    scanner=pattern.scanner,
                    metric=pattern.metric,
                    direction=direction,
                    magnitude="unknown",
                    company_id=document.company_id,
                    ticker=document.ticker,
                    classification=document.classification,
                    subject=None,
                    document_id=document.document_id,
                    document_type=document.document_type,
                    published_at=document.published_at,
                    source_url=document.source_url,
                    evidence_text=sentence,
                    negated=negated,
                    resolved=resolved,
                    extraction_method=match.method,
                    confidence=confidence,
                    matched_phrase=match.text,
                    comparison_basis=_comparison_basis(sentence, pattern),
                    source_section=document.source_section,
                    speaker=document.speaker,
                    speaker_title=document.speaker_title,
                )
            )
    return signals
