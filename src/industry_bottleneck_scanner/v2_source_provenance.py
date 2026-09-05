from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .transcript_store import FileTranscriptStore
from .universe import normalize_ticker


def _feed(hasher: "hashlib._Hash", label: str, payload: bytes) -> None:
    hasher.update(label.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(payload)
    hasher.update(b"\0")


@dataclass(frozen=True)
class SourceResolutionRecord:
    """Freeze the selected transcript provider for one issuer's comparable windows."""

    ticker: str
    provider: str
    quarters: tuple[str, ...]

    def __post_init__(self) -> None:
        ticker = normalize_ticker(self.ticker)
        provider = self.provider.strip()
        quarters = tuple(dict.fromkeys(value.strip().upper() for value in self.quarters))
        if not ticker:
            raise ValueError("ticker is required")
        if not provider:
            raise ValueError("provider is required")
        if not quarters:
            raise ValueError("at least one quarter is required")
        for quarter in quarters:
            if len(quarter) != 6 or quarter[4] != "Q" or quarter[5] not in "1234":
                raise ValueError("quarter must use YYYYQ# format")
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "quarters", quarters)


def normalized_source_resolutions(
    records: Iterable[SourceResolutionRecord],
) -> tuple[SourceResolutionRecord, ...]:
    values = tuple(records)
    tickers = [item.ticker for item in values]
    if len(set(tickers)) != len(tickers):
        raise ValueError("source resolution contains duplicate issuer ticker")
    return tuple(sorted(values, key=lambda item: item.ticker))


def provider_mix_summary(records: Iterable[SourceResolutionRecord]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for item in normalized_source_resolutions(records):
        bucket = summary.setdefault(item.provider, {"issuers": 0, "ticker_quarters": 0})
        bucket["issuers"] += 1
        bucket["ticker_quarters"] += len(item.quarters)
    return dict(sorted(summary.items()))


def missing_resolved_transcripts(
    records: Iterable[SourceResolutionRecord],
    *,
    transcript_root: Path,
) -> tuple[str, ...]:
    store = FileTranscriptStore(transcript_root)
    missing: list[str] = []
    for item in normalized_source_resolutions(records):
        for quarter in item.quarters:
            path = store.path_for(provider=item.provider, ticker=item.ticker, quarter=quarter)
            if not path.exists():
                missing.append(f"{item.provider}:{item.ticker}:{quarter}")
    return tuple(missing)


def compute_v2_source_resolution_fingerprint(
    records: Iterable[SourceResolutionRecord],
    *,
    source_policy_path: Path,
    transcript_root: Path,
) -> str:
    """Hash the v2 source policy, provider selection, and exact normalized transcript bytes.

    This is intentionally separate from frozen-v1 fingerprints. V2 may mix providers across
    issuers, but each issuer has one selected provider for all comparable windows. A change in
    provider selection or normalized transcript bytes must invalidate downstream v2 results.
    """

    values = normalized_source_resolutions(records)
    hasher = hashlib.sha256()
    _feed(hasher, "source_policy", source_policy_path.read_bytes())
    store = FileTranscriptStore(transcript_root)

    for item in values:
        _feed(hasher, f"issuer_provider:{item.ticker}", item.provider.encode("utf-8"))
        _feed(hasher, f"issuer_quarters:{item.ticker}", ",".join(item.quarters).encode("utf-8"))
        for quarter in item.quarters:
            label = f"transcript:{item.provider}:{item.ticker}:{quarter}"
            path = store.path_for(provider=item.provider, ticker=item.ticker, quarter=quarter)
            _feed(hasher, label, path.read_bytes() if path.exists() else b"<missing>")

    return hasher.hexdigest()
