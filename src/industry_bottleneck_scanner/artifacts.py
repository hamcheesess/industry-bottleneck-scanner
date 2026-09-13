from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import AtomicSignal, SourceDocument
from .operating_support import OperatingSupport


def atomic_signal_payload(signal: AtomicSignal) -> dict[str, object]:
    payload = asdict(signal)
    payload["published_at"] = signal.published_at.isoformat()
    return payload


def write_atomic_signals_jsonl(path: Path, signals: Iterable[AtomicSignal]) -> int:
    """Atomically write auditable AtomicSignal records as JSON Lines."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temp_path.open("w", encoding="utf-8") as handle:
        for signal in signals:
            handle.write(json.dumps(atomic_signal_payload(signal), sort_keys=True) + "\n")
            count += 1
    os.replace(temp_path, path)
    return count


def write_source_document_manifest(path: Path, documents: Iterable[SourceDocument]) -> int:
    """Persist document provenance/fingerprints without duplicating full source text."""

    items = tuple(documents)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "source-document-manifest-v1",
        "document_count": len(items),
        "documents": [
            {
                "document_id": item.document_id,
                "company_id": item.company_id,
                "ticker": item.ticker,
                "document_type": item.document_type,
                "published_at": item.published_at.isoformat(),
                "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
                "classification": asdict(item.classification),
                "source_url": item.source_url,
                "source_section": item.source_section,
                "speaker": item.speaker,
                "speaker_title": item.speaker_title,
                "provider": item.provider,
                "content_fingerprint": item.content_fingerprint,
                "text_character_count": len(item.text),
            }
            for item in items
        ],
    }
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)
    return len(items)


def write_operating_support(path: Path, support: OperatingSupport) -> None:
    payload = asdict(support)
    payload["schema_version"] = "operating-support-v1"
    payload["as_of"] = support.as_of.isoformat()
    payload["fresh_coverage_ratio"] = round(support.fresh_coverage_ratio, 6)
    payload["source_type_breadth"] = support.source_type_breadth
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)
