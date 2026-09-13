from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from io import StringIO

from .universe import CANONICAL_UNIVERSE_ID, build_snapshot, normalize_ticker


@dataclass(frozen=True)
class MarketUniverseEntry:
    ticker: str
    sector: str
    bucket: str
    security_id: str | None = None
    issuer_id: str | None = None
    company_name: str | None = None

    def __post_init__(self) -> None:
        if not self.ticker.strip() or not self.sector.strip() or not self.bucket.strip():
            raise ValueError("ticker, sector, and bucket are required")


@dataclass(frozen=True)
class MarketUniverseSnapshot:
    universe_id: str
    as_of: date
    source: str
    active_member_count: int
    entries: tuple[MarketUniverseEntry, ...]
    unclassified_tickers: tuple[str, ...]

    @property
    def classification_coverage_ratio(self) -> float:
        if self.active_member_count == 0:
            return 0.0
        return len(self.entries) / self.active_member_count


def load_market_universe_csv(
    text: str,
    *,
    as_of: date,
    source: str,
    universe_id: str = CANONICAL_UNIVERSE_ID,
) -> MarketUniverseSnapshot:
    """Join the canonical identity snapshot with market aggregation classifications.

    The input extends the existing universe CSV with ``sector`` and ``bucket`` columns.
    Blank classifications remain explicit coverage gaps rather than disappearing from the
    broad-US denominator.
    """

    reader = csv.DictReader(StringIO(text))
    required = {"ticker", "company_name", "sector", "bucket"}
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"market universe CSV missing required columns: {sorted(missing)}")
    rows = list(reader)

    classifications: dict[str, tuple[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        ticker = normalize_ticker(row.get("ticker", ""))
        if ticker in classifications:
            raise ValueError(f"row {row_number}: duplicate normalized ticker {ticker!r}")
        classifications[ticker] = (row.get("sector", "").strip(), row.get("bucket", "").strip())

    identity = build_snapshot(rows, as_of=as_of, source=source, universe_id=universe_id)

    entries: list[MarketUniverseEntry] = []
    unclassified: list[str] = []
    for member in identity.active_members:
        sector, bucket = classifications[member.ticker]
        if not sector or not bucket:
            unclassified.append(member.ticker)
            continue
        entries.append(
            MarketUniverseEntry(
                ticker=member.ticker,
                sector=sector,
                bucket=bucket,
                security_id=member.security_id,
                issuer_id=member.issuer_id,
                company_name=member.company_name,
            )
        )

    return MarketUniverseSnapshot(
        universe_id=identity.universe_id,
        as_of=identity.as_of,
        source=identity.source,
        active_member_count=len(identity.active_members),
        entries=tuple(entries),
        unclassified_tickers=tuple(sorted(unclassified)),
    )
