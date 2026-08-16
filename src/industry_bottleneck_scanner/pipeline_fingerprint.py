from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from .transcript_store import FileTranscriptStore

RESULT_SCHEMA_VERSION = "phase1-batch-v2"

# Files that can change accepted signals, comparable-window construction, aggregation,
# ranking, or the batch result contract. Validation/reporting-only CLIs are excluded.
PIPELINE_SOURCE_FILES: tuple[str, ...] = (
    "aggregation.py",
    "batch_cli.py",
    "batch_orchestration.py",
    "candidate_adjudication.py",
    "candidate_retrieval.py",
    "diagnostics.py",
    "discovery_pipeline.py",
    "discovery_score.py",
    "embedding_adapters.py",
    "experiment.py",
    "models.py",
    "pipeline_fingerprint.py",
    "scanner.py",
    "semantic_retrieval.py",
    "transcript_pipeline.py",
    "transcript_store.py",
    "universe.py",
    "viability.py",
    "vocabulary.py",
)


def _feed(hasher: "hashlib._Hash", label: str, payload: bytes) -> None:
    hasher.update(label.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(payload)
    hasher.update(b"\0")


def compute_pipeline_fingerprint(*, package_root: Path | None = None) -> str:
    root = package_root or Path(__file__).resolve().parent
    hasher = hashlib.sha256()
    _feed(hasher, "result_schema", RESULT_SCHEMA_VERSION.encode("utf-8"))
    for name in sorted(PIPELINE_SOURCE_FILES):
        path = root / name
        if not path.exists():
            raise FileNotFoundError(f"pipeline fingerprint source is missing: {path}")
        _feed(hasher, name, path.read_bytes())
    return hasher.hexdigest()


def _metadata_requests(path: Path) -> tuple[tuple[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if not {"ticker", "quarter"}.issubset(fields):
            raise ValueError(f"{path}: metadata must contain ticker and quarter")
        rows = {
            ((row.get("ticker") or "").strip().upper(), (row.get("quarter") or "").strip().upper())
            for row in reader
            if (row.get("ticker") or "").strip() and (row.get("quarter") or "").strip()
        }
    return tuple(sorted(rows))


def compute_experiment_input_fingerprint(
    *,
    current_metadata: Path,
    baseline_metadata: Path,
    provider: str,
    transcript_root: Path,
) -> str:
    """Hash the exact metadata and normalized transcript-cache inputs used by a batch run."""

    hasher = hashlib.sha256()
    _feed(hasher, "provider", provider.encode("utf-8"))
    for window, metadata in (("current", current_metadata), ("baseline", baseline_metadata)):
        _feed(hasher, f"metadata:{window}", metadata.read_bytes())

    store = FileTranscriptStore(transcript_root)
    requests = {
        (window, ticker, quarter)
        for window, metadata in (("current", current_metadata), ("baseline", baseline_metadata))
        for ticker, quarter in _metadata_requests(metadata)
    }
    for window, ticker, quarter in sorted(requests):
        key = f"transcript:{window}:{provider}:{ticker}:{quarter}"
        path = store.path_for(provider=provider, ticker=ticker, quarter=quarter)
        if path.exists():
            _feed(hasher, key, path.read_bytes())
        else:
            _feed(hasher, key, b"<missing>")
    return hasher.hexdigest()
