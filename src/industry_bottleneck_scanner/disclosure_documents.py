from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .models import Classification, SourceDocument

SUPPORTED_DISCLOSURE_TYPES = frozenset(
    {
        "customer_disclosure",
        "earnings_release",
        "investor_presentation",
        "sec_10k",
        "sec_10q",
        "sec_8k",
        "sec_8k_exhibit",
        "supplier_disclosure",
        "competitor_disclosure",
    }
)


@dataclass(frozen=True)
class DisclosureSection:
    section_id: str
    text: str
    source_section: str | None = None
    speaker: str | None = None
    speaker_title: str | None = None

    def __post_init__(self) -> None:
        if not self.section_id.strip():
            raise ValueError("DisclosureSection.section_id is required")
        if not self.text.strip():
            raise ValueError("DisclosureSection.text is required")


@dataclass(frozen=True)
class PublicDisclosure:
    provider: str
    provider_document_id: str
    company_id: str
    ticker: str | None
    document_type: str
    published_at: datetime
    retrieved_at: datetime
    source_url: str
    sections: tuple[DisclosureSection, ...]
    classification: Classification = field(default_factory=Classification)

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("PublicDisclosure.provider is required")
        if not self.provider_document_id.strip():
            raise ValueError("PublicDisclosure.provider_document_id is required")
        if not self.company_id.strip():
            raise ValueError("PublicDisclosure.company_id is required")
        if self.document_type not in SUPPORTED_DISCLOSURE_TYPES:
            raise ValueError(f"unsupported public disclosure type: {self.document_type}")
        if self.published_at.tzinfo is None or self.retrieved_at.tzinfo is None:
            raise ValueError("public disclosure timestamps must be timezone-aware")
        if not self.source_url.strip():
            raise ValueError("PublicDisclosure.source_url is required")
        if not self.sections:
            raise ValueError("PublicDisclosure.sections must not be empty")
        section_ids = [section.section_id for section in self.sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValueError("PublicDisclosure section IDs must be unique")


def _content_fingerprint(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _document_id(disclosure: PublicDisclosure, section: DisclosureSection) -> str:
    payload = "|".join(
        (
            disclosure.provider,
            disclosure.provider_document_id,
            disclosure.company_id,
            section.section_id,
        )
    )
    return "source-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def disclosure_to_documents(
    disclosure: PublicDisclosure,
    *,
    as_of: datetime | None = None,
) -> tuple[SourceDocument, ...]:
    """Normalize one provider disclosure into stable section-level SourceDocuments."""

    if as_of is not None:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if disclosure.published_at > as_of:
            raise ValueError("public disclosure is later than as_of")

    return tuple(
        SourceDocument(
            document_id=_document_id(disclosure, section),
            company_id=disclosure.company_id,
            ticker=disclosure.ticker,
            document_type=disclosure.document_type,
            published_at=disclosure.published_at,
            text=section.text.strip(),
            classification=disclosure.classification,
            source_url=disclosure.source_url,
            speaker=section.speaker,
            speaker_title=section.speaker_title,
            source_section=section.source_section or section.section_id,
            provider=disclosure.provider,
            retrieved_at=disclosure.retrieved_at,
            content_fingerprint=_content_fingerprint(section.text),
        )
        for section in disclosure.sections
    )


def normalize_disclosures(
    disclosures: Iterable[PublicDisclosure],
    *,
    as_of: datetime | None = None,
) -> tuple[SourceDocument, ...]:
    documents: list[SourceDocument] = []
    seen_ids: set[str] = set()
    for disclosure in disclosures:
        for document in disclosure_to_documents(disclosure, as_of=as_of):
            if document.document_id in seen_ids:
                raise ValueError(f"duplicate normalized SourceDocument: {document.document_id}")
            seen_ids.add(document.document_id)
            documents.append(document)
    return tuple(documents)
