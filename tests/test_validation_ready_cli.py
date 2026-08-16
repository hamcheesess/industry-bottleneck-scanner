import json

from industry_bottleneck_scanner import validation_ready_cli
from industry_bottleneck_scanner.pipeline_fingerprint import RESULT_SCHEMA_VERSION


def _result(
    bucket: str,
    stage: str,
    metrics: list[str],
    aggregation_level: str = "sector",
    *,
    provenance: bool = True,
) -> dict:
    payload = {
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
    if provenance:
        payload["result_provenance"] = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "pipeline_fingerprint": "pipeline-current",
            "input_fingerprint": "input-current",
        }
    return payload


def _metadata_pair(tmp_path, case_id: str) -> None:
    root = tmp_path / "metadata"
    root.mkdir(exist_ok=True)
    text = "ticker,quarter\nAAA,2026Q2\n"
    (root / f"{case_id}-current.csv").write_text(text, encoding="utf-8")
    (root / f"{case_id}-baseline.csv").write_text(text, encoding="utf-8")


def test_ready_validation_uses_only_fresh_results_without_claiming_full_pass(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(validation_ready_cli, "compute_pipeline_fingerprint", lambda: "pipeline-current")
    monkeypatch.setattr(
        validation_ready_cli,
        "compute_experiment_input_fingerprint",
        lambda **kwargs: "input-current",
    )
    for case_id in ("positive", "control"):
        _metadata_pair(tmp_path, case_id)

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

    assert validation_ready_cli.main(
        [
            "--manifest", str(manifest),
            "--base-dir", str(tmp_path),
            "--metadata-root", "metadata",
            "--output", str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "partial_gates_ok"
    assert payload["full_validation_complete"] is False
    assert payload["provisional_gate_ok"] is True
    assert payload["ready_case_ids"] == ["positive", "control"]
    assert payload["missing_case_ids"] == ["blind"]
    assert payload["summary"]["positive_stage_recall"] == 1.0
    assert payload["summary"]["positive_recall"] == 1.0
    assert payload["summary"]["control_false_positive_rate"] == 0.0
    assert "fresh=2/3" in capsys.readouterr().out


def test_unversioned_existing_result_is_stale_not_ready(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(validation_ready_cli, "compute_pipeline_fingerprint", lambda: "pipeline-current")
    _metadata_pair(tmp_path, "positive")
    (tmp_path / "positive.json").write_text(
        json.dumps(_result("Information Technology", "confirmed", ["capacity_constraint"], provenance=False)),
        encoding="utf-8",
    )
    manifest = tmp_path / "cases.csv"
    manifest.write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources\n"
        "positive,positive,positive.json,sector,Information Technology,capacity_constraint,https://example.test/source\n",
        encoding="utf-8",
    )
    output = tmp_path / "ready.json"

    assert validation_ready_cli.main(
        [
            "--manifest", str(manifest),
            "--base-dir", str(tmp_path),
            "--metadata-root", "metadata",
            "--output", str(output),
        ]
    ) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "partial_no_fresh_results"
    assert payload["ready_case_ids"] == []
    assert payload["stale_case_ids"] == ["positive"]
    assert payload["case_freshness"]["positive"]["state"] == "stale_pipeline"
