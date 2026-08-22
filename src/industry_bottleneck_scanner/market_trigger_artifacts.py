from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from .eod_market_data import CollectionDiagnostics
from .market_history import TickerMarketHistory
from .market_trigger import IndustryMarketTrigger, MarketTriggerPolicy

SCHEMA_VERSION = "industry-market-trigger-v1"


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


def write_market_history_jsonl(path: Path, histories: Iterable[TickerMarketHistory]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temp_path.open("w", encoding="utf-8") as handle:
        for history in sorted(histories, key=lambda item: item.ticker):
            for bar in history.bars:
                handle.write(
                    json.dumps(
                        {
                            "adjusted_close": bar.adjusted_close,
                            "bucket": history.bucket,
                            "sector": history.sector,
                            "ticker": history.ticker,
                            "trading_date": bar.trading_date.isoformat(),
                            "volume": bar.volume,
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                count += 1
    os.replace(temp_path, path)
    return count


def write_market_trigger_artifact(
    path: Path,
    *,
    as_of: date,
    benchmark_ticker: str,
    source: str,
    triggers: Iterable[IndustryMarketTrigger],
    policy: MarketTriggerPolicy,
    diagnostics: CollectionDiagnostics,
) -> None:
    _atomic_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "as_of": as_of.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "benchmark_ticker": benchmark_ticker,
            "aggregation": "company_membership_bottom_up",
            "policy": asdict(policy),
            "coverage": asdict(diagnostics),
            "triggers": [asdict(item) for item in triggers],
        },
    )
