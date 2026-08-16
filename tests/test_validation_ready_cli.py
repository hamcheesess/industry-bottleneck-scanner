import json

from industry_bottleneck_scanner.validation_ready_cli import main


def _result(bucket: str, stage: str, metrics: list[str], aggregation_level: str = "sector") -> dict:
    return {
        "aggregation_level": aggregation_level,
        "current": {"clusters": [{"bucket": bucket, "active_metrics": metrics}]},
        "baseline": {"clusters": []},
        "acceleration": [
            {
                "bucket": bucket,
                "watchlisted": stage == "watchlisted",
                "triggered": stage in {"triggered", "confirmed"},
                "confirmed": stage == "confirmed",
                "discovery_score": {"stage": stage, "score": 80.0},
            }
        ],
    }


def test_ready_validation_skips_missing_frozen_results_without_claiming_full_pass(tmp_path, capsys) -> None:
    (tmp_path / "positive.json").write_text(
        json.dumps(_result("Information Technology", "confirmed", ["capacity_constraint", "supply_tightness"])),
        encoding="utf-8",
    )
    (tmp_path / "control.json").write_text(
        json.dumps(_result("Information Technology", "observing", ["backlog_strength"])),
        encoding="utf-8",
    )
    manifest = tmp_path / "cases.csv"
    manifest.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        "positive,positive,positive.json,sector,Information Technology,capacity_constraint|supply_tightness,https://example.test/source,known positive\n"
        "control,control,control.json,sector,,,https://example.test/source,control\n"
        "blind,blind,missing.json,sector,,,,blind\n",
        encoding="utf-8",
    )
    output = tmp_path / "ready.json"

    assert main(["--manifest", str(manifest), "--base-dir", str(tmp_path), "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "partial_gates_ok"
    assert payload["full_validation_complete"] is False
    assert payload["provisional_gate_ok"] is True
    assert payload["missing_case_ids"] == ["blind"]
    assert payload["summary"]["positive_recall"] == 1.0
    assert payload["summary"]["control_false_positive_rate"] == 0.0
    assert "ready=2/3" in capsys.readouterr().out
