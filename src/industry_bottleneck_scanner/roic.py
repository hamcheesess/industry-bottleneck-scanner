from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .alpha_vantage import TranscriptProviderError
from .transcripts import EarningsCallTranscript, TranscriptTurn
from .universe import normalize_ticker

JsonValue = Mapping[str, Any] | list[Any]
JsonTransport = Callable[[str], JsonValue]


def _default_transport(url: str) -> JsonValue:
    request = Request(url, headers={"User-Agent": "industry-bottleneck-scanner/0.1"})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - provider URL is fixed by adapter
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return {"_not_found": True}
        try:
            detail = exc.read().decode("utf-8").strip()
        except Exception:  # pragma: no cover - defensive transport fallback
            detail = ""
        suffix = f": {detail}" if detail else ""
        raise TranscriptProviderError(f"ROIC.ai HTTP {exc.code}{suffix}") from exc
    if not isinstance(payload, (dict, list)):
        raise TranscriptProviderError("ROIC.ai returned a non-JSON-object/list payload")
    return payload


def _validate_quarter(value: str) -> tuple[str, int, int]:
    normalized = value.strip().upper()
    if len(normalized) != 6 or normalized[4] != "Q" or normalized[5] not in "1234":
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2")
    try:
        year = int(normalized[:4])
    except ValueError as exc:
        raise ValueError("quarter must use YYYYQ# format, for example 2026Q2") from exc
    return normalized, year, int(normalized[5])


def _provider_error(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("error") or payload.get("message") or payload.get("detail")
    if not value:
        return None
    return str(value)


def _analyst_title(speaker: str | None) -> str | None:
    if speaker and "analyst" in speaker.casefold():
        return "Analyst"
    return None


@dataclass
class RoicTranscriptSource:
    """Free-tier-capable ROIC.ai fallback for recent earnings-call transcripts.

    The adapter uses ROIC.ai ticker search to resolve an exchange-qualified symbol, then
    requests the structured v3 transcript representation so speaker turns remain explicit.
    This is important because analyst questions must remain distinguishable from issuer
    evidence. Provider plan/history limits are deliberately enforced by ROIC.ai rather than
    hard-coded here.
    """

    api_key: str
    transport: JsonTransport = _default_transport
    search_base_url: str = "https://api.roic.ai/v2/tickers/search"
    transcript_base_url: str = "https://api.roic.ai/v3.0.0/earnings-calls"
    provider_name: str = "roic_ai"

    def build_search_url(self, *, ticker: str) -> str:
        symbol = normalize_ticker(ticker)
        if not symbol:
            raise ValueError("ticker is required")
        return f"{self.search_base_url}?{urlencode({'apikey': self.api_key, 'query': symbol, 'limit': 10})}"

    def _qualified_symbol(self, *, ticker: str) -> str | None:
        symbol = normalize_ticker(ticker)
        payload = self.transport(self.build_search_url(ticker=symbol))
        if not isinstance(payload, list):
            if isinstance(payload, Mapping) and payload.get("_not_found"):
                return None
            if isinstance(payload, Mapping):
                message = _provider_error(payload)
                if message:
                    raise TranscriptProviderError(message)
            raise TranscriptProviderError("ROIC.ai ticker search did not return a list")

        exact = [
            item
            for item in payload
            if isinstance(item, Mapping)
            and normalize_ticker(str(item.get("symbol") or "")) == symbol
            and str(item.get("exchange") or "").strip()
        ]
        if not exact:
            return None

        # Repo A's production universe is US-listed. Prefer the expected US venues when a
        # symbol is duplicated internationally, then fall back to the first exact match.
        preferred = {"NASDAQ": 0, "NYSE": 1, "AMEX": 2}
        exact.sort(key=lambda item: (preferred.get(str(item.get("exchange") or "").upper(), 99), str(item.get("exchange") or "")))
        selected = exact[0]
        exchange = str(selected.get("exchange") or "").strip().upper()
        return f"{exchange}:{symbol}"

    def build_transcript_url(self, *, qualified_symbol: str, quarter: str) -> str:
        _, year, quarter_number = _validate_quarter(quarter)
        identifier = quote(qualified_symbol, safe=":")
        query = urlencode(
            {
                "apikey": self.api_key,
                "fiscal_year": year,
                "fiscal_quarter": quarter_number,
                "format": "json",
            }
        )
        return f"{self.transcript_base_url}/{identifier}?{query}"

    def fetch(self, *, ticker: str, quarter: str) -> EarningsCallTranscript | None:
        symbol = normalize_ticker(ticker)
        fiscal_quarter, _, _ = _validate_quarter(quarter)
        qualified = self._qualified_symbol(ticker=symbol)
        if qualified is None:
            return None

        url = self.build_transcript_url(qualified_symbol=qualified, quarter=fiscal_quarter)
        payload = self.transport(url)
        if not isinstance(payload, Mapping):
            raise TranscriptProviderError("ROIC.ai transcript response did not return an object")
        if payload.get("_not_found"):
            return None
        message = _provider_error(payload)
        if message:
            raise TranscriptProviderError(message)

        transcript = payload.get("transcript")
        if transcript in (None, [], ""):
            return None
        if not isinstance(transcript, list):
            raise TranscriptProviderError("ROIC.ai structured transcript field is not a list")

        turns: list[TranscriptTurn] = []
        for item in transcript:
            if not isinstance(item, Mapping):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            speaker = str(item.get("speaker") or "").strip() or None
            turns.append(
                TranscriptTurn(
                    speaker=speaker,
                    title=_analyst_title(speaker),
                    text=text,
                )
            )

        if not turns:
            return None

        # Keep provenance without persisting the API key embedded in the authenticated URL.
        safe_source_url = self.build_transcript_url(
            qualified_symbol=qualified,
            quarter=fiscal_quarter,
        ).replace(f"apikey={quote(self.api_key)}&", "")

        return EarningsCallTranscript(
            provider=self.provider_name,
            ticker=symbol,
            fiscal_quarter=fiscal_quarter,
            turns=tuple(turns),
            source_url=safe_source_url,
        )
