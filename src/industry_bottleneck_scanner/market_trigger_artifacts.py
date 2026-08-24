from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from .eod_market_data import CollectionDiagnostics
from .market_history import DailyBar, TickerMarketHistory
from .market_trigger import IndustryMarketTrigger, MarketTriggerPolicy
from .market_universe import MarketUniverseEntry, MarketUniverseSnapshot

SCHEMA_VERSION = "industry-market-trigger-v1"


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


@dataclass(frozen=True)
class MarketHistoryArchive:
    as_of: date
    source: str
    benchmark_ticker: str
    benchmark_bars: tuple[DailyBar, ...]
    histories: tuple[TickerMarketHistory, ...]
    diagnostics: CollectionDiagnostics
    universe: MarketUniverseSnapshot


def _universe_payload(universe: MarketUniverseSnapshot) -> dict[str, object]:
    return {
        "universe_id": universe.universe_id,
        "as_of": universe.as_of.isoformat(),
        "source": universe.source,
        "active_member_count": universe.active_member_count,
        "classified_member_count": len(universe.entries),
        "classification_coverage_ratio": round(universe.classification_coverage_ratio, 6),
        "unclassified_tickers": list(universe.unclassified_tickers),
        "entries": [asdict(item) for item in universe.entries],
    }


def write_market_history_jsonl(
    path: Path,
    histories: Iterable[TickerMarketHistory],
    *,
    as_of: date,
    source: str,
    benchmark_ticker: str,
    benchmark_bars: Iterable[DailyBar],
    diagnostics: CollectionDiagnostics,
    universe: MarketUniverseSnapshot,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temp_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "record_type": "manifest",
                    "schema_version": "normalized-market-history-v1",
                    "as_of": as_of.isoformat(),
                    "source": source,
                    "benchmark_ticker": benchmark_ticker,
                    "coverage": asdict(diagnostics),
                    "universe": _universe_payload(universe),
                },
                sort_keys=True,
            )
            + "\n"
        )
        for bar in benchmark_bars:
            handle.write(
                json.dumps(
                    {
                        "record_type": "bar",
                        "role": "benchmark",
                        "ticker": benchmark_ticker,
                        "trading_date": bar.trading_date.isoformat(),
                        "adjusted_close": bar.adjusted_close,
                        "volume": bar.volume,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            count += 1
        for history in sorted(histories, key=lambda item: item.ticker):
            for bar in history.bars:
                handle.write(
                    json.dumps(
                        {
                            "record_type": "bar",
                            "role": "constituent",
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


def load_market_history_jsonl(path: Path) -> MarketHistoryArchive:
    with path.open("r", encoding="utf-8") as handle:
        first_line = next((line for line in handle if line.strip()), None)
        if first_line is None:
            raise ValueError("market history archive must start with a manifest record")
        manifest = json.loads(first_line)
        if manifest.get("record_type") != "manifest":
            raise ValueError("market history archive must start with a manifest record")
        if manifest.get("schema_version") != "normalized-market-history-v1":
            raise ValueError("unsupported market history schema_version")

        benchmark_ticker = str(manifest["benchmark_ticker"])
        benchmark_bars: list[DailyBar] = []
        grouped: dict[tuple[str, str, str], list[DailyBar]] = {}
        for line_number, line in enumerate(handle, start=2):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if record.get("record_type") != "bar":
                raise ValueError("unexpected market history record_type")
            bar = DailyBar(
                trading_date=date.fromisoformat(record["trading_date"]),
                adjusted_close=float(record["adjusted_close"]),
                volume=float(record["volume"]),
            )
            if record.get("role") == "benchmark":
                if record.get("ticker") != benchmark_ticker:
                    raise ValueError("benchmark ticker does not match archive manifest")
                benchmark_bars.append(bar)
            elif record.get("role") == "constituent":
                key = (str(record["ticker"]), str(record["sector"]), str(record["bucket"]))
                grouped.setdefault(key, []).append(bar)
            else:
                raise ValueError("market history bar must have benchmark or constituent role")

    universe_payload = manifest["universe"]
    entries = tuple(MarketUniverseEntry(**item) for item in universe_payload["entries"])
    universe = MarketUniverseSnapshot(
        universe_id=universe_payload["universe_id"],
        as_of=date.fromisoformat(universe_payload["as_of"]),
        source=universe_payload["source"],
        active_member_count=int(universe_payload["active_member_count"]),
        entries=entries,
        unclassified_tickers=tuple(universe_payload["unclassified_tickers"]),
    )
    coverage = manifest["coverage"]
    diagnostics = CollectionDiagnostics(
        requested_tickers=int(coverage["requested_tickers"]),
        loaded_tickers=int(coverage["loaded_tickers"]),
        missing_tickers=tuple(coverage["missing_tickers"]),
        insufficient_history_tickers=tuple(coverage["insufficient_history_tickers"]),
        requested_dates=int(coverage["requested_dates"]),
        provider_dates=int(coverage["provider_dates"]),
        cache_dates=int(coverage["cache_dates"]),
    )
    return MarketHistoryArchive(
        as_of=date.fromisoformat(manifest["as_of"]),
        source=manifest["source"],
        benchmark_ticker=benchmark_ticker,
        benchmark_bars=tuple(sorted(benchmark_bars, key=lambda item: item.trading_date)),
        histories=tuple(
            TickerMarketHistory(
                ticker=ticker,
                sector=sector,
                bucket=bucket,
                bars=tuple(sorted(bars, key=lambda item: item.trading_date)),
            )
            for (ticker, sector, bucket), bars in sorted(grouped.items())
        ),
        diagnostics=diagnostics,
        universe=universe,
    )


def write_market_trigger_artifact(
    path: Path,
    *,
    as_of: date,
    benchmark_ticker: str,
    source: str,
    triggers: Iterable[IndustryMarketTrigger],
    policy: MarketTriggerPolicy,
    diagnostics: CollectionDiagnostics,
    universe: MarketUniverseSnapshot,
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
            "universe": _universe_payload(universe),
            "triggers": [asdict(item) for item in triggers],
        },
    )
