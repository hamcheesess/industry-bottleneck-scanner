from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO

from .universe import normalize_ticker

IWV_HOLDINGS_URL = (
    "https://www.ishares.com/us/products/239714/"
    "ishares-russell-3000-etf/latest-holdings.csv"
)
PROXY_UNIVERSE_ID = "iwv_holdings_validation_proxy"


@dataclass(frozen=True)
class ProxyCandidate:
    company_id: str
    ticker: str
    sector: str
    industry: str
    exchange: str | None
    company_name: str


@dataclass(frozen=True)
class ProxySnapshot:
    as_of: date
    source_url: str
    candidates: tuple[ProxyCandidate, ...]


def parse_iwv_holdings_csv(text: str, *, source_url: str = IWV_HOLDINGS_URL) -> ProxySnapshot:
    """Parse the public IWV holdings CSV into a validation-only broad-US proxy universe.

    IWV exposes sector but not granular industry labels. For the neutral validation sample,
    ``industry`` is therefore explicitly set to ``proxy-sector::<sector>``. This makes the
    limitation visible and causes the cohort sampler's per-industry cap to behave as a
    per-sector cap rather than pretending to have unavailable industry classifications.

    The result is never canonical Russell 3000 membership and must not be used as such.
    """

    lines = text.splitlines()
    if len(lines) < 9:
        raise ValueError("IWV holdings CSV is too short")

    as_of: date | None = None
    header_index: int | None = None
    for index, line in enumerate(lines):
        if line.startswith("Fund Holdings as of,"):
            row = next(csv.reader([line]))
            if len(row) < 2:
                raise ValueError("IWV holdings as-of row is malformed")
            as_of = datetime.strptime(row[1], "%b %d, %Y").date()
        if line.startswith("Ticker,Name,Sector,Asset Class,"):
            header_index = index
            break

    if as_of is None:
        raise ValueError("IWV holdings CSV is missing the as-of date")
    if header_index is None:
        raise ValueError("IWV holdings CSV is missing the holdings header")

    reader = csv.DictReader(StringIO("\n".join(lines[header_index:])))
    candidates: list[ProxyCandidate] = []
    seen_tickers: set[str] = set()
    for row in reader:
        if (row.get("Asset Class") or "").strip().casefold() != "equity":
            continue
        if (row.get("Location") or "").strip().casefold() != "united states":
            continue
        ticker = normalize_ticker(row.get("Ticker") or "")
        sector = (row.get("Sector") or "").strip()
        company_name = (row.get("Name") or "").strip()
        exchange = (row.get("Exchange") or "").strip().upper() or None
        if not ticker or ticker == "-" or not sector or not company_name:
            continue
        if ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)
        candidates.append(
            ProxyCandidate(
                company_id=f"ticker-{ticker}",
                ticker=ticker,
                sector=sector,
                industry=f"proxy-sector::{sector}",
                exchange=exchange,
                company_name=company_name,
            )
        )

    if not candidates:
        raise ValueError("IWV holdings CSV produced no U.S. equity candidates")
    return ProxySnapshot(
        as_of=as_of,
        source_url=source_url,
        candidates=tuple(candidates),
    )


def candidates_to_csv(snapshot: ProxySnapshot) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("company_id", "ticker", "sector", "industry", "exchange"))
    for item in snapshot.candidates:
        writer.writerow((item.company_id, item.ticker, item.sector, item.industry, item.exchange or ""))
    return output.getvalue()
