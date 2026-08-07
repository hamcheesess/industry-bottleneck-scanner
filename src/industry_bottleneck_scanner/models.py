from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ScannerCategory = Literal["capex", "demand", "scarcity", "pricing"]
SignalDirection = Literal["strengthening", "weakening", "stable", "unclear"]
SignalMagnitude = Literal["low", "medium", "high", "unknown"]
ComparisonBasis = Literal[
    "prior_period",
    "prior_guidance_or_plan",
    "threshold",
    "forward_commitment",
    "unspecified",
]


@dataclass(frozen=True)
class Classification:
    sector: str | None = None
    industry: str | None = None
    subindustry: str | None = None


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    company_id: str
    ticker: str | None
    document_type: str
    published_at: datetime
    text: str
    classification: Classification = field(default_factory=Classification)
    source_url: str | None = None


@dataclass(frozen=True)
class AtomicSignal:
    signal_id: str
    scanner: ScannerCategory
    metric: str
    direction: SignalDirection
    magnitude: SignalMagnitude
    company_id: str
    ticker: str | None
    classification: Classification
    subject: str | None
    document_id: str
    document_type: str
    published_at: datetime
    source_url: str | None
    evidence_text: str
    negated: bool
    resolved: bool
    extraction_method: str
    confidence: float
    matched_phrase: str | None = None
    comparison_basis: ComparisonBasis = "unspecified"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
