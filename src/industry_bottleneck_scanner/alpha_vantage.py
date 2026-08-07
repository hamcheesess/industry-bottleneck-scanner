from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .transcripts import EarningsCallTranscript, TranscriptTurn
from .universe import normalize_ticker

JsonTransport = Callable[[str], Mapping[str, Any]]


class TranscriptProviderError(RuntimeError):
    pass


def _default_transport(url: str) -> Mapping[str, Any]:
    request = Request(url, headers={"User-Agent": "industry-bottleneck-scanner/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - provider URL is fixed by adapter
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise TranscriptProviderError("Alpha Vantage returned a non-object JSON payload")
    return payload


def _validate_quarter(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 6 or normalized[4] != "Q" or normalized[5] not in "1234":
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2")
    try:
        year = int(normalized[:4])
    except ValueError as exc:
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2") from exc
    if year < 2010:
        raise ValueError("Alpha Vantage transcript history starts at 2010Q1")
    return normalized


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class AlphaVantageTranscriptSource:
    api_key: str
    transport: JsonTransport = _default_transport
    base_url: str = "https://www.alphavantage.co/query"
    provider_name: str = "alpha_vantage"

    def build_url(self, *, ticker: str, quarter: str) -> str:
        symbol = normalize_ticker(ticker)
        if not symbol:
            raise ValueError("ticker is required")
        fiscal_quarter = _validate_quarter(quarter)
        query = urlencode(
            {
                "function": "EARNINGS_CALL_TRANSCRIPT",
                "symbol": symbol,
                "quarter": fiscal_quarter,
                "apikey": self.api_key,
            }
        )
        return f"{self.base_url}?{query}"

    def fetch(self, *, ticker: str, quarter: str) -> EarningsCallTranscript | None:
        symbol = normalize_ticker(ticker)
        fiscal_quarter = _validate_quarter(quarter)
        payload = self.transport(self.build_url(ticker=symbol, quarter=fiscal_quarter))

        for key in ("Error Message", "Information", "Note"):
            value = payload.get(key)
            if value:
                raise TranscriptProviderError(str(value))

        transcript = payload.get("transcript")
        if transcript in (None, [], ""):
            return None
        if not isinstance(transcript, list):
            raise TranscriptProviderError("Alpha Vantage transcript field is not a list")

        turns: list[TranscriptTurn] = []
        for item in transcript:
            if not isinstance(item, Mapping):
                continue
            text = str(item.get("content") or item.get("speech") or item.get("text") or "").strip()
            if not text:
                continue
            speaker = item.get("speaker")
            title = item.get("title") or item.get("role")
            turns.append(
                TranscriptTurn(
                    speaker=str(speaker).strip() if speaker else None,
                    title=str(title).strip() if title else None,
                    text=text,
                    sentiment=_optional_float(item.get("sentiment")),
                )
            )

        if not turns:
            return None

        return EarningsCallTranscript(
            provider=self.provider_name,
            ticker=symbol,
            fiscal_quarter=fiscal_quarter,
            turns=tuple(turns),
            source_url=self.build_url(ticker=symbol, quarter=fiscal_quarter),
        )
