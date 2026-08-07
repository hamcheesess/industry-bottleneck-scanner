from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from .models import AtomicSignal, SourceDocument
from .vocabulary import DEFAULT_PATTERNS, SignalPattern

_NEGATION_MARKERS = (
    "no longer",
    "not constrained",
    "not capacity constrained",
    "normalized",
    "normalised",
    "improved",
    "declined",
    "decreased",
    "eased",
)


def _sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _signal_id(document_id: str, scanner: str, metric: str, evidence: str) -> str:
    payload = "|".join((document_id, scanner, metric, evidence)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _contains_phrase(sentence: str, phrase: str) -> bool:
    return phrase.casefold() in sentence.casefold()


def _is_negated_or_resolved(sentence: str) -> tuple[bool, bool]:
    lowered = sentence.casefold()
    negated = any(marker in lowered for marker in ("no longer", "not constrained", "not capacity constrained"))
    resolved = negated or any(
        marker in lowered
        for marker in ("normalized", "normalised", "improved", "declined", "decreased", "eased")
    )
    return negated, resolved


def scan_document(
    document: SourceDocument,
    *,
    patterns: tuple[SignalPattern, ...] = DEFAULT_PATTERNS,
) -> list[AtomicSignal]:
    """Run deterministic phrase matching over one normalized source document.

    Phase 1 deliberately keeps extraction simple and auditable. A later extractor may
    enrich subject, magnitude, and semantic direction without changing the output contract.
    """

    signals: list[AtomicSignal] = []
    for sentence in _sentences(document.text):
        negated, resolved = _is_negated_or_resolved(sentence)
        for pattern in patterns:
            if not any(_contains_phrase(sentence, phrase) for phrase in pattern.phrases):
                continue

            direction = "weakening" if resolved else pattern.direction
            confidence = 0.55 if resolved else 0.75
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
                    extraction_method="keyword",
                    confidence=confidence,
                )
            )
    return signals
