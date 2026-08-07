from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import AtomicSignal


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
