from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from io import StringIO

from .universe import normalize_ticker


@dataclass(frozen=True)
class CohortCandidate:
    company_id: str
    ticker: str
    sector: str
    industry: str
    exchange: str | None = None


@dataclass(frozen=True)
class CohortSelectionDiagnostics:
    candidate_companies: int
    selected_companies: int
    sectors_available: int
    sectors_selected: int
    industries_selected: int
    max_per_industry: int
    seed: str


@dataclass(frozen=True)
class NeutralCohortSelection:
    companies: tuple[CohortCandidate, ...]
    diagnostics: CohortSelectionDiagnostics


def load_cohort_candidates_csv(text: str) -> tuple[CohortCandidate, ...]:
    reader = csv.DictReader(StringIO(text))
    required = {"company_id", "ticker", "sector", "industry"}
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"cohort candidate CSV missing required columns: {sorted(missing)}")

    records: list[CohortCandidate] = []
    seen_ids: set[str] = set()
    seen_tickers: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        company_id = (row.get("company_id") or "").strip()
        ticker = normalize_ticker(row.get("ticker") or "")
        sector = (row.get("sector") or "").strip()
        industry = (row.get("industry") or "").strip()
        exchange = (row.get("exchange") or "").strip().upper() or None
        if not company_id or not ticker or not sector or not industry:
            raise ValueError(f"row {row_number}: company_id, ticker, sector, and industry are required")
        if company_id in seen_ids:
            raise ValueError(f"row {row_number}: duplicate company_id {company_id!r}")
        if ticker in seen_tickers:
            raise ValueError(f"row {row_number}: duplicate ticker {ticker!r}")
        seen_ids.add(company_id)
        seen_tickers.add(ticker)
        records.append(
            CohortCandidate(
                company_id=company_id,
                ticker=ticker,
                sector=sector,
                industry=industry,
                exchange=exchange,
            )
        )

    if not records:
        raise ValueError("cohort candidate CSV must contain at least one record")
    return tuple(records)


def _stable_rank(seed: str, *parts: str) -> str:
    payload = "|".join((seed, *parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def select_neutral_cohort(
    candidates: tuple[CohortCandidate, ...],
    *,
    target_size: int = 10,
    max_per_industry: int = 2,
    seed: str = "phase1-neutral-v1",
) -> NeutralCohortSelection:
    """Select a reproducible cross-sector cohort without using signal outcomes.

    Selection uses only identity/classification metadata. It cycles across sectors and caps
    any one industry so known bottleneck names or scanner outputs cannot influence the
    sample. Stable hashing gives deterministic ordering without depending on input order.
    """

    if target_size < 1:
        raise ValueError("target_size must be at least 1")
    if max_per_industry < 1:
        raise ValueError("max_per_industry must be at least 1")
    if not candidates:
        raise ValueError("candidates must not be empty")

    by_sector: dict[str, list[CohortCandidate]] = {}
    for candidate in candidates:
        by_sector.setdefault(candidate.sector, []).append(candidate)
    for sector, items in by_sector.items():
        items.sort(key=lambda item: _stable_rank(seed, sector, item.company_id, item.ticker))

    sector_order = sorted(by_sector, key=lambda sector: _stable_rank(seed, "sector", sector))
    positions = {sector: 0 for sector in sector_order}
    industry_counts: dict[str, int] = {}
    selected: list[CohortCandidate] = []

    while len(selected) < min(target_size, len(candidates)):
        added_this_round = False
        for sector in sector_order:
            items = by_sector[sector]
            position = positions[sector]
            while position < len(items):
                candidate = items[position]
                position += 1
                positions[sector] = position
                if industry_counts.get(candidate.industry, 0) >= max_per_industry:
                    continue
                selected.append(candidate)
                industry_counts[candidate.industry] = industry_counts.get(candidate.industry, 0) + 1
                added_this_round = True
                break
            if len(selected) >= target_size:
                break
        if not added_this_round:
            break

    selected_sectors = {item.sector for item in selected}
    selected_industries = {item.industry for item in selected}
    return NeutralCohortSelection(
        companies=tuple(selected),
        diagnostics=CohortSelectionDiagnostics(
            candidate_companies=len(candidates),
            selected_companies=len(selected),
            sectors_available=len(by_sector),
            sectors_selected=len(selected_sectors),
            industries_selected=len(selected_industries),
            max_per_industry=max_per_industry,
            seed=seed,
        ),
    )
