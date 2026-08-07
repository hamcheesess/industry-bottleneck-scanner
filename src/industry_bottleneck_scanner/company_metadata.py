from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

from .models import Classification
from .universe import normalize_ticker


@dataclass(frozen=True)
class CompanyPeriodMetadata:
    ticker: str
    company_id: str
    quarter: str
    published_at: datetime
    classification: Classification


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("published_at is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("published_at must include a timezone offset")
    return parsed


def load_company_period_metadata_csv(text: str) -> tuple[CompanyPeriodMetadata, ...]:
    """Load explicit, dated metadata used to scan cached earnings calls.

    The manifest deliberately requires a real publication/call timestamp. Fiscal-quarter
    labels are not converted into dates because doing so would contaminate acceleration
    windows for companies with non-calendar fiscal years.
    """

    reader = csv.DictReader(StringIO(text))
    required = {"ticker", "company_id", "quarter", "published_at"}
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"metadata CSV missing required columns: {sorted(missing)}")

    records: list[CompanyPeriodMetadata] = []
    seen: set[tuple[str, str]] = set()
    for row_number, row in enumerate(reader, start=2):
        ticker = normalize_ticker(row.get("ticker", ""))
        company_id = row.get("company_id", "").strip()
        quarter = row.get("quarter", "").strip().upper()
        if not ticker:
            raise ValueError(f"row {row_number}: ticker is required")
        if not company_id:
            raise ValueError(f"row {row_number}: company_id is required")
        if len(quarter) != 6 or quarter[4] != "Q" or quarter[5] not in "1234":
            raise ValueError(f"row {row_number}: quarter must use YYYYQ# format")
        key = (ticker, quarter)
        if key in seen:
            raise ValueError(f"row {row_number}: duplicate ticker/quarter {ticker} {quarter}")
        seen.add(key)

        records.append(
            CompanyPeriodMetadata(
                ticker=ticker,
                company_id=company_id,
                quarter=quarter,
                published_at=_parse_datetime(row.get("published_at", "")),
                classification=Classification(
                    sector=row.get("sector", "").strip() or None,
                    industry=row.get("industry", "").strip() or None,
                    subindustry=row.get("subindustry", "").strip() or None,
                ),
            )
        )

    if not records:
        raise ValueError("metadata CSV must contain at least one record")
    return tuple(records)
