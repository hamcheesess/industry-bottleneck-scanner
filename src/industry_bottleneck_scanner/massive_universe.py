from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import urlopen

from .eod_market_data import MarketDataError
from .universe import CANONICAL_UNIVERSE_ID, normalize_cik, normalize_ticker

SCHEMA_VERSION = "massive-universe-bootstrap-v1"
SOURCE_ID = "massive_reference_v3"

# Massive normally returns the operating MIC XNAS for Nasdaq listings, but the
# additional Nasdaq MICs keep the filter stable if the provider exposes them later.
US_PRIMARY_EXCHANGES = frozenset(
    {
        "ARCX",  # NYSE Arca
        "BATS",  # Cboe BZX
        "XASE",  # NYSE American
        "XNAS",  # Nasdaq
        "XNCM",  # Nasdaq Capital Market
        "XNGS",  # Nasdaq Global Select
        "XNMS",  # Nasdaq Global Market
        "XNYS",  # New York Stock Exchange
    }
)


@dataclass(frozen=True)
class MassiveTickerReference:
    ticker: str
    company_name: str
    primary_exchange: str | None
    cik: str | None
    composite_figi: str | None
    share_class_figi: str | None
    ticker_type: str | None
    active: bool
    locale: str | None
    market: str | None


@dataclass(frozen=True)
class MassiveTickerOverview:
    ticker: str
    company_name: str
    primary_exchange: str | None
    cik: str | None
    composite_figi: str | None
    share_class_figi: str | None
    sic_code: str | None
    sic_description: str | None


@dataclass(frozen=True)
class MassiveUniverseDiagnostics:
    provider_reference_count: int
    canonical_member_count: int
    classified_member_count: int
    unclassified_member_count: int
    pending_overview_count: int
    overview_error_count: int
    overview_error_tickers: tuple[str, ...]
    provider_requests: int
    cache_hits: int
    enrichment_status: str

    @property
    def enrichment_complete(self) -> bool:
        return self.pending_overview_count == 0


@dataclass(frozen=True)
class MassiveUniverseBuild:
    rows: tuple[dict[str, str], ...]
    diagnostics: MassiveUniverseDiagnostics


class MassiveHttpError(MarketDataError):
    def __init__(self, status_code: int):
        super().__init__(f"Massive HTTP {status_code}")
        self.status_code = status_code


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _normalized_sic(value: object) -> str | None:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if not digits:
        return None
    return digits.zfill(4)[-4:]


def sic_division(sic_code: str | None) -> str | None:
    """Return the explicit SIC division used as the market-relative sector.

    This is deliberately not labelled as GICS. The provider SIC code remains the
    classification authority, and the range mapping only makes the aggregation stable.
    """

    normalized = _normalized_sic(sic_code)
    if normalized is None:
        return None
    value = int(normalized)
    if 100 <= value <= 999:
        return "SIC Division A — Agriculture, Forestry, and Fishing"
    if 1000 <= value <= 1499:
        return "SIC Division B — Mining"
    if 1500 <= value <= 1799:
        return "SIC Division C — Construction"
    if 2000 <= value <= 3999:
        return "SIC Division D — Manufacturing"
    if 4000 <= value <= 4999:
        return "SIC Division E — Transportation, Communications, Electric, Gas, and Sanitary Services"
    if 5000 <= value <= 5199:
        return "SIC Division F — Wholesale Trade"
    if 5200 <= value <= 5999:
        return "SIC Division G — Retail Trade"
    if 6000 <= value <= 6799:
        return "SIC Division H — Finance, Insurance, and Real Estate"
    if 7000 <= value <= 8999:
        return "SIC Division I — Services"
    if 9100 <= value <= 9729:
        return "SIC Division J — Public Administration"
    if 9900 <= value <= 9999:
        return "SIC Division K — Nonclassifiable Establishments"
    return None


def sic_bucket(sic_code: str | None, description: str | None) -> str | None:
    normalized = _normalized_sic(sic_code)
    if normalized is None:
        return None
    label = (description or "").strip()
    return f"SIC {normalized} — {label}" if label else f"SIC {normalized}"


class MassiveReferenceClient:
    """Cache-first Massive reference-data adapter with Basic-plan pacing."""

    base_url = "https://api.massive.com"

    def __init__(
        self,
        *,
        api_key: str,
        cache_dir: Path,
        request_interval_seconds: float = 13.0,
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
        self.provider_requests = 0
        self.cache_hits = 0

    @staticmethod
    def _open_url(url: str) -> bytes:
        try:
            with urlopen(url, timeout=60) as response:  # noqa: S310 - fixed provider host
                return response.read()
        except HTTPError as exc:
            raise MassiveHttpError(exc.code) from exc

    def _request(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "api.massive.com":
            raise MarketDataError("Massive pagination returned an unexpected provider host")
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["apiKey"] = self._api_key
        authenticated_url = urlunparse(parsed._replace(query=urlencode(query)))
        if self._last_request_at is not None and self._request_interval_seconds:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self._request_interval_seconds:
                time.sleep(self._request_interval_seconds - elapsed)
        try:
            self.provider_requests += 1
            raw = self._transport(authenticated_url)
            return raw
        finally:
            self._last_request_at = time.monotonic()

    @staticmethod
    def _validate_payload(raw: bytes, *, context: str) -> dict[str, object]:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MarketDataError(f"invalid Massive response for {context}") from exc
        if not isinstance(payload, dict):
            raise MarketDataError(f"invalid Massive response object for {context}")
        if payload.get("status") not in {None, "OK", "DELAYED"}:
            message = payload.get("error") or payload.get("message") or payload.get("status")
            raise MarketDataError(f"Massive response error for {context}: {message}")
        return payload

    def _read_or_request(self, cache_path: Path, *, url: str, context: str) -> dict[str, object]:
        if cache_path.exists():
            raw = cache_path.read_bytes()
            payload = self._validate_payload(raw, context=context)
            self.cache_hits += 1
            return payload
        raw = self._request(url)
        payload = self._validate_payload(raw, context=context)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
        temporary.write_bytes(raw)
        os.replace(temporary, cache_path)
        return payload

    def list_active_common_stocks(self, *, as_of: date) -> tuple[MassiveTickerReference, ...]:
        query = urlencode(
            {
                "active": "true",
                "date": as_of.isoformat(),
                "limit": "1000",
                "locale": "us",
                "market": "stocks",
                "order": "asc",
                "sort": "ticker",
                "type": "CS",
            }
        )
        next_url: str | None = f"{self.base_url}/v3/reference/tickers?{query}"
        page = 1
        results: list[MassiveTickerReference] = []
        seen_tickers: set[str] = set()
        while next_url:
            cache_path = (
                self._cache_dir
                / "all-tickers-v1"
                / f"as_of={as_of.isoformat()}"
                / f"page-{page:05d}.json"
            )
            payload = self._read_or_request(
                cache_path,
                url=next_url,
                context=f"all tickers page {page}",
            )
            raw_results = payload.get("results") or ()
            if not isinstance(raw_results, list):
                raise MarketDataError(f"invalid Massive ticker results on page {page}")
            for item in raw_results:
                if not isinstance(item, Mapping):
                    continue
                ticker = normalize_ticker(str(item.get("ticker", "")))
                if not ticker:
                    continue
                if ticker in seen_tickers:
                    raise MarketDataError(f"duplicate Massive ticker reference: {ticker}")
                seen_tickers.add(ticker)
                results.append(
                    MassiveTickerReference(
                        ticker=ticker,
                        company_name=str(item.get("name", "")).strip(),
                        primary_exchange=_optional_string(item.get("primary_exchange")),
                        cik=normalize_cik(_optional_string(item.get("cik"))),
                        composite_figi=_optional_string(item.get("composite_figi")),
                        share_class_figi=_optional_string(item.get("share_class_figi")),
                        ticker_type=_optional_string(item.get("type")),
                        active=bool(item.get("active", True)),
                        locale=_optional_string(item.get("locale")),
                        market=_optional_string(item.get("market")),
                    )
                )
            next_value = payload.get("next_url")
            next_url = str(next_value) if next_value else None
            page += 1
        return tuple(results)

    def _overview_cache_path(self, ticker: str, *, as_of: date) -> Path:
        fingerprint = hashlib.sha256(ticker.encode("utf-8")).hexdigest()[:20]
        return (
            self._cache_dir
            / "ticker-overview-v1"
            / f"as_of={as_of.isoformat()}"
            / f"{fingerprint}.json"
        )

    def has_cached_overview(self, ticker: str, *, as_of: date) -> bool:
        return self._overview_cache_path(ticker, as_of=as_of).exists()

    def _overview_error_path(self, ticker: str, *, as_of: date) -> Path:
        return self._overview_cache_path(ticker, as_of=as_of).with_suffix(".error.json")

    def cached_overview_error(self, ticker: str, *, as_of: date) -> int | None:
        path = self._overview_error_path(ticker, as_of=as_of)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MarketDataError(f"invalid cached Massive overview error for {ticker}") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "massive-overview-terminal-error-v1"
            or normalize_ticker(str(payload.get("ticker") or "")) != normalize_ticker(ticker)
            or payload.get("http_status") not in {400, 404}
        ):
            raise MarketDataError(f"invalid cached Massive overview error for {ticker}")
        return int(payload["http_status"])

    def record_overview_error(self, ticker: str, *, as_of: date, status_code: int) -> None:
        if status_code not in {400, 404}:
            raise ValueError("only terminal per-ticker Massive errors may be checkpointed")
        _atomic_write(
            self._overview_error_path(ticker, as_of=as_of),
            json.dumps(
                {
                    "schema_version": "massive-overview-terminal-error-v1",
                    "ticker": normalize_ticker(ticker),
                    "as_of": as_of.isoformat(),
                    "http_status": status_code,
                },
                sort_keys=True,
            )
            + "\n",
        )

    def fetch_overview(self, ticker: str, *, as_of: date) -> MassiveTickerOverview:
        normalized_ticker = normalize_ticker(ticker)
        encoded_ticker = urlencode({"ticker": normalized_ticker}).split("=", 1)[1]
        query = urlencode({"date": as_of.isoformat()})
        url = f"{self.base_url}/v3/reference/tickers/{encoded_ticker}?{query}"
        payload = self._read_or_request(
            self._overview_cache_path(normalized_ticker, as_of=as_of),
            url=url,
            context=f"ticker overview {normalized_ticker}",
        )
        result = payload.get("results")
        if not isinstance(result, Mapping):
            raise MarketDataError(f"Massive ticker overview missing results for {normalized_ticker}")
        returned_ticker = normalize_ticker(str(result.get("ticker", normalized_ticker)))
        if returned_ticker != normalized_ticker:
            raise MarketDataError(f"Massive ticker overview mismatch for {normalized_ticker}")
        return MassiveTickerOverview(
            ticker=normalized_ticker,
            company_name=str(result.get("name", "")).strip(),
            primary_exchange=_optional_string(result.get("primary_exchange")),
            cik=normalize_cik(_optional_string(result.get("cik"))),
            composite_figi=_optional_string(result.get("composite_figi")),
            share_class_figi=_optional_string(result.get("share_class_figi")),
            sic_code=_normalized_sic(result.get("sic_code")),
            sic_description=_optional_string(result.get("sic_description")),
        )


def _is_canonical_reference(item: MassiveTickerReference) -> bool:
    exchange = (item.primary_exchange or "").upper()
    return (
        item.active
        and (item.locale or "").lower() == "us"
        and (item.market or "").lower() == "stocks"
        and (item.ticker_type or "").upper() == "CS"
        and exchange in US_PRIMARY_EXCHANGES
        and bool(item.company_name)
    )


def _row(reference: MassiveTickerReference, overview: MassiveTickerOverview | None) -> dict[str, str]:
    detail = overview
    cik = detail.cik if detail and detail.cik else reference.cik
    share_class_figi = (
        detail.share_class_figi if detail and detail.share_class_figi else reference.share_class_figi
    )
    composite_figi = (
        detail.composite_figi if detail and detail.composite_figi else reference.composite_figi
    )
    security_figi = share_class_figi or composite_figi
    sic_code = detail.sic_code if detail else None
    return {
        "security_id": f"figi-{security_figi}" if security_figi else "",
        "issuer_id": f"cik-{cik}" if cik else "",
        "ticker": reference.ticker,
        "company_name": (detail.company_name if detail and detail.company_name else reference.company_name),
        "exchange": (detail.primary_exchange if detail and detail.primary_exchange else reference.primary_exchange) or "",
        "cik": cik or "",
        "memberships": CANONICAL_UNIVERSE_ID,
        "active": "true",
        "sector": sic_division(sic_code) or "",
        "bucket": sic_bucket(sic_code, detail.sic_description if detail else None) or "",
        "classification_system": "SEC_SIC" if sic_code else "",
        "classification_code": sic_code or "",
    }


def build_massive_universe(
    client: MassiveReferenceClient,
    *,
    as_of: date,
    max_overview_requests: int,
) -> MassiveUniverseBuild:
    if max_overview_requests < 0:
        raise ValueError("max_overview_requests must be non-negative")
    references = client.list_active_common_stocks(as_of=as_of)
    canonical = tuple(sorted(filter(_is_canonical_reference, references), key=lambda item: item.ticker))
    rows: list[dict[str, str]] = []
    pending = 0
    overview_errors: list[str] = []
    overview_requests = 0
    for reference in canonical:
        cached = client.has_cached_overview(reference.ticker, as_of=as_of)
        terminal_error = client.cached_overview_error(reference.ticker, as_of=as_of)
        overview: MassiveTickerOverview | None = None
        if terminal_error is not None:
            overview_errors.append(reference.ticker)
        elif cached or overview_requests < max_overview_requests:
            before = client.provider_requests
            try:
                overview = client.fetch_overview(reference.ticker, as_of=as_of)
            except MassiveHttpError as exc:
                if exc.status_code not in {400, 404}:
                    raise
                client.record_overview_error(
                    reference.ticker,
                    as_of=as_of,
                    status_code=exc.status_code,
                )
                overview_errors.append(reference.ticker)
            finally:
                if client.provider_requests > before:
                    overview_requests += 1
        else:
            pending += 1
        rows.append(_row(reference, overview))

    classified = sum(bool(row["sector"] and row["bucket"]) for row in rows)
    if pending:
        status = "enrichment_in_progress"
    elif classified == len(rows) and not overview_errors:
        status = "complete"
    else:
        status = "complete_with_classification_gaps"
    return MassiveUniverseBuild(
        rows=tuple(rows),
        diagnostics=MassiveUniverseDiagnostics(
            provider_reference_count=len(references),
            canonical_member_count=len(rows),
            classified_member_count=classified,
            unclassified_member_count=len(rows) - classified,
            pending_overview_count=pending,
            overview_error_count=len(overview_errors),
            overview_error_tickers=tuple(sorted(overview_errors)),
            provider_requests=client.provider_requests,
            cache_hits=client.cache_hits,
            enrichment_status=status,
        ),
    )


CSV_FIELDS = (
    "security_id",
    "issuer_id",
    "ticker",
    "company_name",
    "exchange",
    "cik",
    "memberships",
    "active",
    "sector",
    "bucket",
    "classification_system",
    "classification_code",
)


def rows_to_csv(rows: Iterable[Mapping[str, str]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
    return buffer.getvalue()


def write_massive_universe_artifacts(
    *,
    csv_path: Path,
    manifest_path: Path,
    build: MassiveUniverseBuild,
    as_of: date,
    request_interval_seconds: float,
) -> None:
    csv_text = rows_to_csv(build.rows)
    _atomic_write(csv_path, csv_text)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "universe_id": CANONICAL_UNIVERSE_ID,
        "as_of": as_of.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_ID,
        "classification": {
            "system": "SEC_SIC",
            "sector_semantics": "SEC SIC division",
            "bucket_semantics": "SEC SIC code and provider description",
        },
        "free_plan_execution": {
            "request_interval_seconds": request_interval_seconds,
            "checkpointed_raw_cache": True,
        },
        "diagnostics": asdict(build.diagnostics),
        "normalized_csv_sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
    }
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
