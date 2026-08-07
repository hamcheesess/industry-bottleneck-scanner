from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .transcript_collection import CollectionItem, TranscriptRequest
from .transcript_store import FileTranscriptStore


@dataclass(frozen=True)
class PilotDiagnostics:
    provider: str
    requested_pairs: int
    resolved_pairs: int
    available_pairs: int
    missing_pairs: int
    failed_pairs: int
    paired_companies: int
    fully_available_companies: int
    average_turns_available: float
    ready_for_matched_experiment: bool
    unresolved_pairs: tuple[tuple[str, str], ...]

    @property
    def resolved_rate(self) -> float:
        return 0.0 if self.requested_pairs == 0 else self.resolved_pairs / self.requested_pairs

    @property
    def availability_rate(self) -> float:
        return 0.0 if self.requested_pairs == 0 else self.available_pairs / self.requested_pairs


def _item_from_json(item: dict[str, object]) -> CollectionItem:
    return CollectionItem(
        ticker=str(item.get("ticker") or ""),
        quarter=str(item.get("quarter") or ""),
        status=str(item.get("status") or ""),
        turn_count=int(item.get("turn_count") or 0),
        error=str(item["error"]) if item.get("error") is not None else None,
    )


def load_collection_items(path: Path) -> tuple[str, tuple[CollectionItem, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    provider = str(payload.get("provider") or "")
    if not provider:
        raise ValueError("collection result is missing provider")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("collection result items must be a list")
    return provider, tuple(_item_from_json(item) for item in raw_items if isinstance(item, dict))


def diagnose_pilot(
    *,
    provider: str,
    requests: Iterable[TranscriptRequest],
    items: Iterable[CollectionItem],
    transcript_store: FileTranscriptStore,
    min_paired_companies: int = 3,
) -> PilotDiagnostics:
    if min_paired_companies < 1:
        raise ValueError("min_paired_companies must be at least 1")

    request_list = tuple(requests)
    item_by_pair = {(item.ticker, item.quarter): item for item in items}
    requested_by_ticker: dict[str, set[str]] = {}
    available_by_ticker: dict[str, set[str]] = {}
    unresolved: list[tuple[str, str]] = []
    available_turns: list[int] = []
    missing_pairs = 0
    failed_pairs = 0
    available_pairs = 0

    for request in request_list:
        requested_by_ticker.setdefault(request.ticker, set()).add(request.quarter)
        item = item_by_pair.get((request.ticker, request.quarter))
        cached = transcript_store.load(provider=provider, ticker=request.ticker, quarter=request.quarter)
        if cached is not None:
            available_pairs += 1
            available_by_ticker.setdefault(request.ticker, set()).add(request.quarter)
            available_turns.append(len(cached.turns))
            continue

        if item is None or item.status in {"budget_exhausted", "rate_limited"}:
            unresolved.append((request.ticker, request.quarter))
            continue
        if item.status == "missing":
            missing_pairs += 1
            continue
        failed_pairs += 1

    paired_companies = sum(len(quarters) >= 2 for quarters in requested_by_ticker.values())
    fully_available_companies = sum(
        len(quarters) >= 2 and quarters.issubset(available_by_ticker.get(ticker, set()))
        for ticker, quarters in requested_by_ticker.items()
    )
    resolved_pairs = available_pairs + missing_pairs + failed_pairs
    average_turns = sum(available_turns) / len(available_turns) if available_turns else 0.0

    return PilotDiagnostics(
        provider=provider,
        requested_pairs=len(request_list),
        resolved_pairs=resolved_pairs,
        available_pairs=available_pairs,
        missing_pairs=missing_pairs,
        failed_pairs=failed_pairs,
        paired_companies=paired_companies,
        fully_available_companies=fully_available_companies,
        average_turns_available=average_turns,
        ready_for_matched_experiment=(
            fully_available_companies >= min_paired_companies and not unresolved
        ),
        unresolved_pairs=tuple(unresolved),
    )
