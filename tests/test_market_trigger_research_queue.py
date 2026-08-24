from __future__ import annotations

import csv
import json

import pytest

from industry_bottleneck_scanner.market_trigger_research_queue import (
    build_persistent_research_queue,
)
from industry_bottleneck_scanner.market_trigger_research_queue_cli import main


def _inputs(tmp_path):
    review = tmp_path / "quality.json"
    review.write_text(
        json.dumps(
            {
                "schema_version": "market-trigger-quality-review-v1",
                "review_mode": "outcome_blind_market_data_only",
                "promotion_status": "research_queue_ready",
                "policy_decision": "frozen_no_threshold_change",
                "archive_as_of": "2026-08-21",
                "universe": {"as_of": "2025-05-30"},
                "latest_bucket_stability": [
                    {
                        "bucket": "Stable",
                        "research_tier": "persistent",
                        "current_consecutive_run": 3,
                        "triggered_date_count": 5,
                        "latest_score": 80.0,
                    },
                    {
                        "bucket": "New",
                        "research_tier": "emerging",
                        "current_consecutive_run": 1,
                        "triggered_date_count": 1,
                        "latest_score": 99.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    universe = tmp_path / "universe.csv"
    universe.write_text(
        "issuer_id,cik,ticker,company_name,sector,bucket\n"
        "cik-1,1,AAA,Alpha,Industrials,Stable\n"
        "cik-2,2,BBB,Beta,Industrials,Stable\n"
        "cik-3,3,CCC,Gamma,Technology,New\n",
        encoding="utf-8",
    )
    return review, universe


def test_queue_selects_all_persistent_issuers_and_excludes_emerging(tmp_path) -> None:
    review, universe = _inputs(tmp_path)
    output = tmp_path / "queue"
    payload = build_persistent_research_queue(
        review,
        universe,
        output_dir=output,
        batch_size=1,
    )

    assert payload["outcome_data_used"] is False
    assert payload["thresholds_changed"] is False
    assert payload["selected_issuer_count"] == 2
    assert len(payload["batches"]) == 2
    with (output / "sec_issuers_batch_001.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["ticker"] for row in rows] == ["AAA"]


def test_queue_records_missing_cik_without_silently_counting_it(tmp_path) -> None:
    review, universe = _inputs(tmp_path)
    universe.write_text(
        universe.read_text().replace("cik-2,2,BBB", "cik-2,,BBB"),
        encoding="utf-8",
    )
    payload = build_persistent_research_queue(
        review,
        universe,
        output_dir=tmp_path / "queue",
    )
    assert payload["selected_issuer_count"] == 1
    assert payload["missing_cik_tickers"] == ["BBB"]


def test_queue_deduplicates_share_classes_at_sec_issuer_boundary(tmp_path) -> None:
    review, universe = _inputs(tmp_path)
    universe.write_text(
        universe.read_text()
        + "cik-1,1,AAA.B,Alpha Class B,Industrials,Stable\n",
        encoding="utf-8",
    )
    payload = build_persistent_research_queue(
        review,
        universe,
        output_dir=tmp_path / "queue",
    )
    assert payload["selected_issuer_count"] == 2
    assert payload["duplicate_security_tickers"] == ["AAA.B"]


def test_queue_rejects_non_outcome_blind_review(tmp_path) -> None:
    review, universe = _inputs(tmp_path)
    payload = json.loads(review.read_text())
    payload["review_mode"] = "outcome_aware"
    review.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="outcome-blind"):
        build_persistent_research_queue(review, universe, output_dir=tmp_path / "queue")


def test_queue_cli_reports_bounded_batches(tmp_path, capsys) -> None:
    review, universe = _inputs(tmp_path)
    assert main(
        [
            "--quality-review",
            str(review),
            "--universe-csv",
            str(universe),
            "--output-dir",
            str(tmp_path / "queue"),
            "--batch-size",
            "1",
        ]
    ) == 0
    assert "status=ready provider_calls=0 buckets=1 issuers=2 batches=2" in capsys.readouterr().out
