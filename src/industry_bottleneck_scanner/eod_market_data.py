from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from .market_history import DailyBar, MIN_REQUIRED_TRADING_DAYS, TickerMarketHistory


class MarketDataError(RuntimeError):
    """A provider or normalized market-history collection failure."""


@dataclass(frozen=True)
class MarketUniverseEntry:
    ticker: str
    sector: str
    bucket: str

    def __post_init__(self) -> None:
        if not self.ticker.strip() or not self.sector.strip() or not self.bucket.strip():
            raise ValueError("ticker, sector, and bucket are required")


@dataclass(frozen=True)
class CollectionDiagnostics:
    requested_tickers: int
    loaded_tickers: int
    missing_tickers: tuple[str, ...]
    insufficient_history_tickers: tuple[str, ...]
    requested_dates: int
    provider_dates: int
    cache_dates: int


@dataclass(frozen=True)
class CollectedMarketHistory:
    histories: tuple[TickerMarketHistory, ...]
    benchmark_bars: tuple[DailyBar, ...]
    diagnostics: CollectionDiagnostics


class MassiveGroupedDailyClient:
    """Cache-first adapter for Massive's all-US-stocks grouped daily endpoint.

    Provider-specific response fields are normalized here. Downstream market modules only
    receive ``DailyBar`` and ``TickerMarketHistory`` contracts.
    """

    base_url = "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks"

    def __init__(
        self,
        *,
        api_key: str,
        cache_dir: Path,
        request_interval_seconds: float = 0.0,
        transport: Callable[[str], bytes] | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Massive API key is required")
        if request_interval_seconds < 0:
            raise ValueError("request_interval_seconds must be non-negative")
        self._api_key = api_key
        self._cache_dir = cache_dir
        self._request_interval_seconds = request_interval_seconds
        self._transport = transport or self._open_url
        self._last_request_at: float | None = None
        self.provider_dates = 0
        self.cache_dates = 0

    @staticmethod
    def _open_url(url: str) -> bytes:
        try:
            with urlopen(url, timeout=60) as response:  # noqa: S310 - fixed provider host
                return response.read()
        except HTTPError as exc:
            raise MarketDataError(f"Massive HTTP {exc.code}") from exc

    def _cache_path(self, trading_date: date) -> Path:
        return self._cache_dir / f"{trading_date.isoformat()}.json"

    def _request(self, trading_date: date) -> bytes:
        if self._last_request_at is not None and self._request_interval_seconds:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self._request_interval_seconds:
                time.sleep(self._request_interval_seconds - elapsed)
        query = urlencode({"adjusted": "true", "apiKey": self._api_key})
        url = f"{self.base_url}/{trading_date.isoformat()}?{query}"
        try:
            return self._transport(url)
        finally:
            self._last_request_at = time.monotonic()

    def fetch_day(self, trading_date: date) -> Mapping[str, DailyBar]:
        cache_path = self._cache_path(trading_date)
        from_cache = cache_path.exists()
        if from_cache:
            raw = cache_path.read_bytes()
            self.cache_dates += 1
        else:
            raw = self._request(trading_date)

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MarketDataError(f"invalid Massive response for {trading_date}") from exc
        if payload.get("status") not in {None, "OK", "DELAYED"}:
            message = payload.get("error") or payload.get("message") or payload.get("status")
            raise MarketDataError(f"Massive response error for {trading_date}: {message}")
        if not from_cache:
            # Cache only validated responses. Quota/authentication failures must be retryable.
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            temp_path = cache_path.with_suffix(".json.tmp")
            temp_path.write_bytes(raw)
            os.replace(temp_path, cache_path)
            self.provider_dates += 1

        result: dict[str, DailyBar] = {}
        for item in payload.get("results") or ():
            ticker = str(item.get("T", "")).strip().upper()
            close = item.get("c")
            volume = item.get("v", 0)
            if not ticker or close is None:
                continue
            result[ticker] = DailyBar(
                trading_date=trading_date,
                adjusted_close=float(close),
                volume=float(volume),
            )
        return result


def calendar_dates(start: date, end: date) -> tuple[date, ...]:
    if start > end:
        raise ValueError("start must be on or before end")
    return tuple(start + timedelta(days=offset) for offset in range((end - start).days + 1))


def collect_grouped_market_history(
    entries: Iterable[MarketUniverseEntry],
    *,
    benchmark_ticker: str,
    start: date,
    as_of: date,
    client: MassiveGroupedDailyClient,
) -> CollectedMarketHistory:
    items = tuple(entries)
    if not items:
        raise ValueError("at least one market-universe entry is required")
    normalized_tickers = tuple(item.ticker.upper() for item in items)
    if len(set(normalized_tickers)) != len(normalized_tickers):
        raise ValueError("market-universe tickers must be unique")
    by_ticker: dict[str, list[DailyBar]] = {ticker: [] for ticker in normalized_tickers}
    benchmark = benchmark_ticker.strip().upper()
    if not benchmark:
        raise ValueError("benchmark_ticker is required")
    benchmark_bars: list[DailyBar] = []

    requested_dates = calendar_dates(start, as_of)
    for trading_date in requested_dates:
        # Weekend calls cannot produce regular-session bars and unnecessarily consume quota.
        if trading_date.weekday() >= 5:
            continue
        bars = client.fetch_day(trading_date)
        for ticker, target in by_ticker.items():
            if ticker in bars:
                target.append(bars[ticker])
        if benchmark in bars:
            benchmark_bars.append(bars[benchmark])

    histories = tuple(
        TickerMarketHistory(
            ticker=item.ticker.upper(),
            sector=item.sector,
            bucket=item.bucket,
            bars=tuple(by_ticker[item.ticker.upper()]),
        )
        for item in items
        if len(by_ticker[item.ticker.upper()]) >= MIN_REQUIRED_TRADING_DAYS
    )
    missing = tuple(sorted(ticker for ticker, bars in by_ticker.items() if not bars))
    insufficient = tuple(
        sorted(
            ticker
            for ticker, bars in by_ticker.items()
            if bars and len(bars) < MIN_REQUIRED_TRADING_DAYS
        )
    )
    return CollectedMarketHistory(
        histories=histories,
        benchmark_bars=tuple(benchmark_bars),
        diagnostics=CollectionDiagnostics(
            requested_tickers=len(items),
            loaded_tickers=len(histories),
            missing_tickers=missing,
            insufficient_history_tickers=insufficient,
            requested_dates=sum(day.weekday() < 5 for day in requested_dates),
            provider_dates=client.provider_dates,
            cache_dates=client.cache_dates,
        ),
    )
