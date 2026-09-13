from datetime import date

import pytest

from industry_bottleneck_scanner.universe import (
    CANONICAL_UNIVERSE_ID,
    build_snapshot,
    load_snapshot_csv,
    normalize_cik,
    normalize_ticker,
)


def test_normalizes_ticker_and_cik() -> None:
    assert normalize_ticker(" brk.b ") == "BRK-B"
    assert normalize_cik("320193") == "0000320193"


def test_builds_snapshot_and_tracks_sec_resolution() -> None:
    snapshot = build_snapshot(
        [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "exchange": "nasdaq",
                "cik": "320193",
                "memberships": "sp500;nasdaq100",
            },
            {
                "ticker": "TEST",
                "company_name": "Test Corp",
                "exchange": "nyse",
            },
        ],
        as_of=date(2026, 8, 7),
        source="fixture",
    )

    assert snapshot.universe_id == CANONICAL_UNIVERSE_ID
    assert len(snapshot.active_members) == 2
    assert len(snapshot.sec_resolvable_members) == 1
    assert len(snapshot.unresolved_members) == 1
    apple = snapshot.members[0]
    assert apple.cik == "0000320193"
    assert apple.issuer_id == "cik-0000320193"
    assert apple.memberships == (
        "broad_us_common_stocks_v1",
        "sp500",
        "nasdaq100",
    )


def test_preserves_multiple_share_classes_for_one_issuer() -> None:
    snapshot = build_snapshot(
        [
            {
                "ticker": "AAA.A",
                "company_name": "Example Holdings",
                "exchange": "NYSE",
                "cik": "12345",
            },
            {
                "ticker": "AAA.B",
                "company_name": "Example Holdings",
                "exchange": "NYSE",
                "cik": "12345",
            },
        ],
        as_of=date(2026, 8, 7),
        source="fixture",
    )

    assert len(snapshot.members) == 2
    assert snapshot.members[0].issuer_id == snapshot.members[1].issuer_id
    assert snapshot.members[0].security_id != snapshot.members[1].security_id


def test_rejects_duplicate_security_ids() -> None:
    with pytest.raises(ValueError, match="duplicate security_id"):
        build_snapshot(
            [
                {
                    "security_id": "same",
                    "ticker": "AAA",
                    "company_name": "A",
                },
                {
                    "security_id": "same",
                    "ticker": "BBB",
                    "company_name": "B",
                },
            ],
            as_of=date(2026, 8, 7),
            source="fixture",
        )


def test_load_snapshot_csv_requires_core_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        load_snapshot_csv(
            "ticker,exchange\nAAA,NYSE\n",
            as_of=date(2026, 8, 7),
            source="fixture",
        )
