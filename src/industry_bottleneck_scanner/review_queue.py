from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .candidate_adjudication import AdjudicationResult, promote_candidate
from .candidate_retrieval import RetrievalCandidate
from .models import AtomicSignal, Classification, SourceDocument


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    candidate: RetrievalCandidate
    company_id: str
    ticker: str | None
    document_type: str
    published_at: datetime
    classification: Classification
    source_url: str | None
    speaker: str | None
    speaker_title: str | None
    source_section: str | None
    status: str = "pending"
    decision_reason: str | None = None

    @classmethod
    def from_candidate(cls, candidate: RetrievalCandidate, document: SourceDocument) -> "ReviewRecord":
        payload = "|".join(
            (
                document.document_id,
                candidate.scanner,
                candidate.metric,
                " ".join(candidate.evidence_text.casefold().split()),
            )
        ).encode("utf-8")
        review_id = hashlib.sha256(payload).hexdigest()[:24]
        return cls(
            review_id=review_id,
            candidate=candidate,
            company_id=document.company_id,
            ticker=document.ticker,
            document_type=document.document_type,
            published_at=document.published_at,
            classification=document.classification,
            source_url=document.source_url,
            speaker=document.speaker,
            speaker_title=document.speaker_title,
            source_section=document.source_section,
        )

    def as_document(self) -> SourceDocument:
        return SourceDocument(
            document_id=self.candidate.document_id,
            company_id=self.company_id,
            ticker=self.ticker,
            document_type=self.document_type,
            published_at=self.published_at,
            text=self.candidate.evidence_text,
            classification=self.classification,
            source_url=self.source_url,
            speaker=self.speaker,
            speaker_title=self.speaker_title,
            source_section=self.source_section,
        )


class FileReviewQueue:
    """Small auditable JSON review queue with atomic rewrites and deterministic IDs."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> tuple[ReviewRecord, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        records: list[ReviewRecord] = []
        for item in payload:
            candidate_data = item["candidate"]
            candidate = RetrievalCandidate(
                document_id=candidate_data["document_id"],
                scanner=candidate_data["scanner"],
                metric=candidate_data["metric"],
                evidence_text=candidate_data["evidence_text"],
                methods=tuple(candidate_data["methods"]),
                score=float(candidate_data["score"]),
                review_tier=candidate_data["review_tier"],
            )
            classification = Classification(**item["classification"])
            records.append(
                ReviewRecord(
                    review_id=item["review_id"],
                    candidate=candidate,
                    company_id=item["company_id"],
                    ticker=item.get("ticker"),
                    document_type=item["document_type"],
                    published_at=datetime.fromisoformat(item["published_at"]),
                    classification=classification,
                    source_url=item.get("source_url"),
                    speaker=item.get("speaker"),
                    speaker_title=item.get("speaker_title"),
                    source_section=item.get("source_section"),
                    status=item.get("status", "pending"),
                    decision_reason=item.get("decision_reason"),
                )
            )
        return tuple(records)

    def _write(self, records: tuple[ReviewRecord, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for record in records:
            item = asdict(record)
            item["published_at"] = record.published_at.isoformat()
            payload.append(item)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp_path, self.path)

    def enqueue(self, records: tuple[ReviewRecord, ...]) -> int:
        existing = {record.review_id: record for record in self.load()}
        added = 0
        for record in records:
            if record.review_id in existing:
                continue
            existing[record.review_id] = record
            added += 1
        self._write(tuple(existing[key] for key in sorted(existing)))
        return added

    def pending(self) -> tuple[ReviewRecord, ...]:
        return tuple(record for record in self.load() if record.status == "pending")

    def resolve(self, review_id: str, *, accepted: bool, reason: str) -> AtomicSignal | None:
        records = list(self.load())
        for index, record in enumerate(records):
            if record.review_id != review_id:
                continue
            status = "accepted" if accepted else "rejected"
            updated = ReviewRecord(
                **{
                    **record.__dict__,
                    "status": status,
                    "decision_reason": reason,
                }
            )
            records[index] = updated
            self._write(tuple(records))
            if not accepted:
                return None
            decision = AdjudicationResult(updated.candidate, "accepted", reason)
            return promote_candidate(decision, updated.as_document())
        raise KeyError(f"unknown review_id: {review_id}")
