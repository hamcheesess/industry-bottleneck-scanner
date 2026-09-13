from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from industry_bottleneck_scanner.market_trigger_quality import (
    build_market_trigger_quality_review,
)
from industry_bottleneck_scanner.market_trigger_quality_cli import main


POLICY = {"min_companies": 4}
UNIVERSE = {
    "universe_id": "broad_us_common_stocks_v1",
    "as_of": "2025-05-30",
    "source": "test",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _calibration(tmp_path: Path) -> Path:
    root = tmp_path / "calibration"
    dates = []
    values = {
        "2025-05-30": {"A"},
        "2025-06-30": {"A", "B"},
        "2025-07-31": {"A", "B", "C"},
    }
    for as_of, triggered in values.items():
        path = root / f"as_of={as_of}" / "industry_market_triggers.json"
        path.parent.mkdir(parents=True)
        payload = {
            "schema_version": "industry-market-trigger-v1",
            "as_of": as_of,
            "policy": POLICY,
            "universe": UNIVERSE,
            "triggers": [
                {
                    "bucket": bucket,
                    "score": score,
                    "company_count": 5,
                    "triggered": bucket in triggered,
                }
                for bucket, score in (("A", 80), ("B", 70), ("C", 60), ("D", 20))
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        dates.append(
            {
                "as_of": as_of,
                "artifact_path": str(path.relative_to(root)),
                "artifact_sha256": _sha(path),
            }
        )
    manifest = {
        "schema_version": "market-trigger-calibration-v1",
        "provider_calls": 0,
        "policy_status": "frozen_observation_only_no_threshold_tuning",
        "archive_as_of": "2025-07-31",
        "calibration_window": {"start_as_of": "2025-05-30", "end_as_of": "2025-07-31"},
        "universe": UNIVERSE,
        "policy": POLICY,
        "dates": dates,
    }
    (root / "calibration_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_quality_review_classifies_persistent_and_emerging_without_outcomes(tmp_path) -> None:
    root = _calibration(tmp_path)
    output = tmp_path / "quality.json"
    payload = build_market_trigger_quality_review(root, output_path=output)

    by_bucket = {item["bucket"]: item for item in payload["latest_bucket_stability"]}
    assert payload["review_mode"] == "outcome_blind_market_data_only"
    assert payload["policy_decision"] == "frozen_no_threshold_change"
    assert payload["provider_calls"] == 0
    assert payload["summary"]["latest_persistent_bucket_count"] == 2
    assert payload["summary"]["latest_emerging_bucket_count"] == 1
    assert by_bucket["A"]["current_consecutive_run"] == 3
    assert by_bucket["B"]["current_consecutive_run"] == 2
    assert by_bucket["C"]["research_tier"] == "emerging"
    assert output.exists()


def test_quality_review_fails_closed_on_artifact_mutation(tmp_path) -> None:
    root = _calibration(tmp_path)
    artifact = root / "as_of=2025-06-30" / "industry_market_triggers.json"
    artifact.write_text(artifact.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_market_trigger_quality_review(root, output_path=tmp_path / "quality.json")


def test_quality_cli_reports_provider_free_queue(tmp_path, capsys) -> None:
    root = _calibration(tmp_path)
    output = tmp_path / "quality.json"
    assert main(["--calibration-dir", str(root), "--output", str(output)]) == 0
    assert "status=research_queue_ready provider_calls=0" in capsys.readouterr().out
