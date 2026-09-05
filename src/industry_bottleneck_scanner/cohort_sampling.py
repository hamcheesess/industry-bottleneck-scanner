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
    companies_per_industry: int
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
    industry_count: int = 3,
    companies_per_industry: int = 4,
    seed: str = "phase1-neutral-v2",
) -> NeutralCohortSelection:
    """Select a reproducible blind cohort with enough within-industry breadth to trigger.

    The previous cross-sector sampler capped each industry below the production trigger's
    minimum-company requirement, making an industry-level blind discovery impossible by
    construction. This sampler instead selects industries without using scanner outcomes,
    then takes a fixed number of issuers inside each selected industry. Industries are
    spread across sectors when possible and all ordering is stable-hash based.
    """

    if industry_count < 1:
        raise ValueError("industry_count must be at least 1")
    if companies_per_industry < 3:
        raise ValueError("companies_per_industry must be at least 3 for Phase-1 industry triggers")
    if not candidates:
        raise ValueError("candidates must not be empty")

    by_industry: dict[tuple[str, str], list[CohortCandidate]] = {}
    for candidate in candidates:
        by_industry.setdefault((candidate.sector, candidate.industry), []).append(candidate)

    eligible_industries = {
        key: tuple(
            sorted(
                items,
                key=lambda item: _stable_rank(seed, "company", item.company_id, item.ticker),
            )
        )
        for key, items in by_industry.items()
        if len(items) >= companies_per_industry
    }
    if not eligible_industries:
        raise ValueError("no industry has enough companies for the requested within-industry breadth")

    by_sector: dict[str, list[tuple[str, str]]] = {}
    for key in eligible_industries:
        by_sector.setdefault(key[0], []).append(key)
    for sector, keys in by_sector.items():
        keys.sort(key=lambda key: _stable_rank(seed, "industry", sector, key[1]))

    sector_order = sorted(by_sector, key=lambda sector: _stable_rank(seed, "sector", sector))
    positions = {sector: 0 for sector in sector_order}
    selected_industries: list[tuple[str, str]] = []

    while len(selected_industries) < min(industry_count, len(eligible_industries)):
        added = False
        for sector in sector_order:
            position = positions[sector]
            keys = by_sector[sector]
            if position >= len(keys):
                continue
            selected_industries.append(keys[position])
            positions[sector] = position + 1
            added = True
            if len(selected_industries) >= industry_count:
                break
        if not added:
            break

    selected: list[CohortCandidate] = []
    for key in selected_industries:
        selected.extend(eligible_industries[key][:companies_per_industry])

    selected_sectors = {item.sector for item in selected}
    return NeutralCohortSelection(
        companies=tuple(selected),
        diagnostics=CohortSelectionDiagnostics(
            candidate_companies=len(candidates),
            selected_companies=len(selected),
            sectors_available=len({item.sector for item in candidates}),
            sectors_selected=len(selected_sectors),
            industries_selected=len(selected_industries),
            companies_per_industry=companies_per_industry,
            seed=seed,
        ),
    )
