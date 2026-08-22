import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from industry_bottleneck_scanner.massive_universe import (
    MassiveReferenceClient,
    build_massive_universe,
    rows_to_csv,
    sic_bucket,
    sic_division,
    write_massive_universe_artifacts,
)
from industry_bottleneck_scanner.market_universe import load_market_universe_csv
from industry_bottleneck_scanner.universe import CANONICAL_UNIVERSE_ID


AS_OF = date(2026, 8, 21)


def response(payload: object) -> bytes:
    return json.dumps(payload).encode()


def ticker(ticker_symbol: str, *, exchange: str = "XNAS", ticker_type: str = "CS") -> dict:
    return {
        "ticker": ticker_symbol,
        "name": f"{ticker_symbol} Company",
        "primary_exchange": exchange,
        "cik": "12345",
        "share_class_figi": f"FIGI-{ticker_symbol}",
        "type": ticker_type,
        "active": True,
        "locale": "us",
        "market": "stocks",
    }


def overview(ticker_symbol: str, sic_code: str = "3571") -> dict:
    return {
        "status": "OK",
        "results": {
            **ticker(ticker_symbol),
            "sic_code": sic_code,
            "sic_description": "Electronic Computers",
        },
    }


def test_lists_paginated_common_stocks_and_defensively_filters_exchange_and_type(tmp_path) -> None:
    requested: list[str] = []

    def transport(url: str) -> bytes:
        requested.append(url)
        parsed = urlparse(url)
        if parsed.path == "/v3/reference/tickers" and "cursor" not in parse_qs(parsed.query):
            return response(
                {
                    "status": "OK",
                    "results": [ticker("AAA"), ticker("OTC", exchange="OTCM")],
                    "next_url": "https://api.massive.com/v3/reference/tickers?cursor=next",
                }
            )
        if parsed.path == "/v3/reference/tickers":
            return response(
                {
                    "status": "OK",
                    "results": [ticker("BBB", exchange="XNYS"), ticker("ETF", ticker_type="ETF")],
                }
            )
        symbol = parsed.path.rsplit("/", 1)[-1]
        return response(overview(symbol))

    client = MassiveReferenceClient(
        api_key="secret",
        cache_dir=tmp_path,
        request_interval_seconds=0,
        transport=transport,
    )
    build = build_massive_universe(client, as_of=AS_OF, max_overview_requests=10)

    assert [row["ticker"] for row in build.rows] == ["AAA", "BBB"]
    first_query = parse_qs(urlparse(requested[0]).query)
    assert first_query["type"] == ["CS"]
    assert first_query["date"] == [AS_OF.isoformat()]
    assert all(parse_qs(urlparse(url).query)["apiKey"] == ["secret"] for url in requested)
    assert build.diagnostics.enrichment_status == "complete"


def test_overview_budget_resumes_from_raw_cache_without_repeating_requests(tmp_path) -> None:
    requested: list[str] = []

    def transport(url: str) -> bytes:
        requested.append(url)
        parsed = urlparse(url)
        if parsed.path == "/v3/reference/tickers":
            return response({"status": "OK", "results": [ticker("AAA"), ticker("BBB")]})
        return response(overview(parsed.path.rsplit("/", 1)[-1]))

    first_client = MassiveReferenceClient(
        api_key="secret",
        cache_dir=tmp_path,
        request_interval_seconds=0,
        transport=transport,
    )
    first = build_massive_universe(first_client, as_of=AS_OF, max_overview_requests=1)
    assert first.diagnostics.pending_overview_count == 1
    assert first.diagnostics.enrichment_status == "enrichment_in_progress"
    assert requested.count(requested[0]) == 1

    second_client = MassiveReferenceClient(
        api_key="secret",
        cache_dir=tmp_path,
        request_interval_seconds=0,
        transport=transport,
    )
    second = build_massive_universe(second_client, as_of=AS_OF, max_overview_requests=1)
    assert second.diagnostics.pending_overview_count == 0
    assert second.diagnostics.classified_member_count == 2
    assert second.diagnostics.provider_requests == 1
    assert len(requested) == 3  # all-tickers + one overview in each run


def test_sic_classification_is_explicit_and_round_trips_market_universe(tmp_path) -> None:
    assert sic_division("3571") == "SIC Division D — Manufacturing"
    assert sic_bucket("3571", "Electronic Computers") == "SIC 3571 — Electronic Computers"

    client = MassiveReferenceClient(
        api_key="secret",
        cache_dir=tmp_path / "cache",
        request_interval_seconds=0,
        transport=lambda url: (
            response({"status": "OK", "results": [ticker("AAA")]})
            if urlparse(url).path == "/v3/reference/tickers"
            else response(overview("AAA"))
        ),
    )
    build = build_massive_universe(client, as_of=AS_OF, max_overview_requests=1)
    csv_text = rows_to_csv(build.rows)
    snapshot = load_market_universe_csv(
        csv_text,
        as_of=AS_OF,
        source="massive_reference_v3",
    )

    assert snapshot.universe_id == CANONICAL_UNIVERSE_ID
    assert snapshot.active_member_count == 1
    assert snapshot.classification_coverage_ratio == 1.0
    assert snapshot.entries[0].bucket == "SIC 3571 — Electronic Computers"


def test_manifest_records_checkpoint_status_and_normalized_fingerprint(tmp_path) -> None:
    client = MassiveReferenceClient(
        api_key="secret",
        cache_dir=tmp_path / "cache",
        request_interval_seconds=0,
        transport=lambda _: response({"status": "OK", "results": [ticker("AAA")]}),
    )
    build = build_massive_universe(client, as_of=AS_OF, max_overview_requests=0)
    csv_path = tmp_path / "universe.csv"
    manifest_path = tmp_path / "manifest.json"
    write_massive_universe_artifacts(
        csv_path=csv_path,
        manifest_path=manifest_path,
        build=build,
        as_of=AS_OF,
        request_interval_seconds=13.0,
    )

    manifest = json.loads(manifest_path.read_text())
    assert manifest["universe_id"] == CANONICAL_UNIVERSE_ID
    assert manifest["diagnostics"]["enrichment_status"] == "enrichment_in_progress"
    assert len(manifest["normalized_csv_sha256"]) == 64
