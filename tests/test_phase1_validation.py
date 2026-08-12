import json
from pathlib import Path

import pytest

from industry_bottleneck_scanner.phase1_validation import (
    evaluate_validation_manifest,
    load_validation_cases_csv,
)


def _write_result(
    path: Path,
    *,
    bucket: str,
    stage: str,
    score: float,
    metrics: list[str],
    aggregation_level: str = "industry",
) -> None:
    flags = {
        "watchlisted": stage == "watchlisted",
        "triggered": stage in {"triggered", "confirmed"},
        "confirmed": stage == "confirmed",
    }
    path.write_text(
        json.dumps(
            {
                "aggregation_level": aggregation_level,
                "acceleration": [
                    {
                        "bucket": bucket,
                        **flags,
                        "discovery_score": {"stage": stage, "score": score},
                    }
                ],
                "current": {
                    "clusters": [
                        {
                            "bucket": bucket,
                            "active_metrics": metrics,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )


def test_validation_reports_positive_recovery_and_control_false_positive_rate(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "positive.json",
        bucket="Electrical Equipment",
        stage="triggered",
        score=82.0,
        metrics=["backlog_strength", "capacity_constraint"],
    )
    _write_result(
        tmp_path / "control.json",
        bucket="Software",
        stage="observing",
        score=31.0,
        metrics=["capacity_expansion"],
    )
    manifest = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        "known-positive,positive,positive.json,industry,Electrical Equipment,backlog_strength|capacity_constraint,https://example.test/label,\n"
        "negative-control,control,control.json,industry,,,https://example.test/context,\n"
    )

    report = evaluate_validation_manifest(manifest, base_dir=tmp_path)

    assert report.summary.positive_recall == 1.0
    assert report.summary.control_false_positive_rate == 0.0
    assert report.summary.expected_metric_recall == 1.0
    assert report.summary.aggregation_mismatches == 0
    assert report.cases[0].positive_recovered is True
    assert report.cases[0].label_sources == ("https://example.test/label",)
    assert report.cases[1].control_false_positive is False


def test_positive_requires_watchlist_or_stronger_and_expected_metrics(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "result.json",
        bucket="Electrical Equipment",
        stage="observing",
        score=58.0,
        metrics=["backlog_strength"],
    )
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
        "case-a,positive,result.json,industry,Electrical Equipment,backlog_strength|capacity_constraint,https://example.test/label\n"
    )

    report = evaluate_validation_manifest(cases, base_dir=tmp_path)

    assert report.summary.positive_recall == 0.0
    assert report.summary.expected_metric_recall == 0.5
    assert report.cases[0].expected_metric_hits == ("backlog_strength",)
    assert report.cases[0].expected_metric_misses == ("capacity_constraint",)


def test_blind_case_has_no_label_based_pass_fail(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "blind.json",
        bucket="Information Technology",
        stage="watchlisted",
        score=64.0,
        metrics=["bookings_strength"],
        aggregation_level="sector",
    )
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,label_sources\n"
        "blind-a,blind,blind.json,sector,\n"
    )

    report = evaluate_validation_manifest(cases, base_dir=tmp_path)

    assert report.summary.blind_cases == 1
    assert report.cases[0].positive_recovered is None
    assert report.cases[0].control_false_positive is None
    assert report.cases[0].strongest_bucket == "Information Technology"


def test_positive_manifest_requires_source_backing() -> None:
    with pytest.raises(ValueError, match="positive cases require at least one label source URL"):
        load_validation_cases_csv(
            "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
            "case-a,positive,result.json,sector,Information Technology,capacity_constraint,\n"
        )


def test_label_sources_must_be_http_urls() -> None:
    with pytest.raises(ValueError, match="label_sources must contain http"):
        load_validation_cases_csv(
            "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
            "case-a,positive,result.json,sector,Information Technology,capacity_constraint,not-a-url\n"
        )


def test_aggregation_level_mismatch_blocks_positive_recovery(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "result.json",
        bucket="Information Technology",
        stage="triggered",
        score=80.0,
        metrics=["capacity_constraint"],
        aggregation_level="sector",
    )
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
        "case-a,positive,result.json,industry,Information Technology,capacity_constraint,https://example.test/label\n"
    )

    report = evaluate_validation_manifest(cases, base_dir=tmp_path)

    assert report.summary.aggregation_mismatches == 1
    assert report.cases[0].aggregation_level_matches is False
    assert report.cases[0].positive_recovered is False
