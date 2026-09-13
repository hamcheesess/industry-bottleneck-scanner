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
                "current": {"clusters": [{"bucket": bucket, "active_metrics": metrics}]},
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

    assert report.summary.positive_stage_recall == 1.0
    assert report.summary.positive_recall == 1.0
    assert report.summary.control_false_positive_rate == 0.0
    assert report.summary.expected_metric_recall == 1.0
    assert report.summary.aggregation_mismatches == 0
    assert report.cases[0].positive_stage_recovered is True
    assert report.cases[0].positive_recovered is True
    assert report.cases[0].label_sources == ("https://example.test/label",)
    assert report.cases[1].control_false_positive is False


def test_stage_recovery_is_reported_separately_from_exact_metric_recovery(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "result.json",
        bucket="Electrical Equipment",
        stage="confirmed",
        score=88.0,
        metrics=["backlog_strength"],
    )
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
        "case-a,positive,result.json,industry,Electrical Equipment,backlog_strength|capacity_constraint,https://example.test/label\n"
    )

    report = evaluate_validation_manifest(cases, base_dir=tmp_path)

    assert report.summary.positive_stage_recall == 1.0
    assert report.summary.positive_recall == 0.0
    assert report.summary.expected_metric_recall == 0.5
    assert report.cases[0].positive_stage_recovered is True
    assert report.cases[0].positive_recovered is False
    assert report.cases[0].expected_metric_misses == ("capacity_constraint",)


def test_observing_positive_fails_stage_and_strict_recovery(tmp_path: Path) -> None:
    _write_result(
        tmp_path / "result.json",
        bucket="Electrical Equipment",
        stage="observing",
        score=58.0,
        metrics=["backlog_strength", "capacity_constraint"],
    )
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
        "case-a,positive,result.json,industry,Electrical Equipment,backlog_strength|capacity_constraint,https://example.test/label\n"
    )

    report = evaluate_validation_manifest(cases, base_dir=tmp_path)

    assert report.summary.positive_stage_recall == 0.0
    assert report.summary.positive_recall == 0.0
    assert report.summary.expected_metric_recall == 1.0


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
    assert report.cases[0].positive_stage_recovered is None
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


def test_manifest_accepts_explicit_operational_metadata_paths() -> None:
    cases = load_validation_cases_csv(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,current_metadata_path,baseline_metadata_path\n"
        "case-a,positive,result.json,industry,Electrical Equipment,backlog_strength,https://example.test/label,experiments/current.csv,experiments/baseline.csv\n"
    )
    assert cases[0].current_metadata_path == "experiments/current.csv"
    assert cases[0].baseline_metadata_path == "experiments/baseline.csv"


def test_manifest_rejects_one_sided_operational_metadata_path() -> None:
    with pytest.raises(ValueError, match="must be supplied together"):
        load_validation_cases_csv(
            "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,current_metadata_path,baseline_metadata_path\n"
            "case-a,positive,result.json,industry,Electrical Equipment,backlog_strength,https://example.test/label,experiments/current.csv,\n"
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
    assert report.cases[0].positive_stage_recovered is False
    assert report.cases[0].positive_recovered is False
