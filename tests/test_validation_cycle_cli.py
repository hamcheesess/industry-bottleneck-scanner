import json
from pathlib import Path

from industry_bottleneck_scanner import validation_cycle_cli


def test_cycle_consolidates_run_freshness_and_calibration(monkeypatch, tmp_path: Path, capsys) -> None:
    run_status = tmp_path / "run.json"
    ready_output = tmp_path / "ready.json"
    calibration_output = tmp_path / "calibration.json"
    cycle_output = tmp_path / "cycle.json"

    def fake_run(argv):
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(json.dumps({"status": "partial", "completed_cases": 4}), encoding="utf-8")
        print("noisy run output")
        return 0

    def fake_ready(argv):
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "status": "partial_gates_not_met",
                    "total_frozen_cases": 7,
                    "ready_case_ids": ["a", "b", "c", "d"],
                    "missing_case_ids": ["e", "f", "g"],
                    "stale_case_ids": [],
                    "blocked_input_case_ids": [],
                    "summary": {
                        "positive_recall": 1 / 3,
                        "positive_stage_recall": 2 / 3,
                        "expected_metric_recall": 6 / 7,
                        "control_false_positive_rate": 0.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        print("noisy ready output")
        return 0

    def fake_calibration(argv):
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(json.dumps({"status": "diagnosed"}), encoding="utf-8")
        print("noisy calibration output")
        return 0

    monkeypatch.setattr(validation_cycle_cli, "validation_run_main", fake_run)
    monkeypatch.setattr(validation_cycle_cli, "ready_main", fake_ready)
    monkeypatch.setattr(validation_cycle_cli, "calibration_main", fake_calibration)

    assert validation_cycle_cli.main(
        [
            "--run-status", str(run_status),
            "--ready-output", str(ready_output),
            "--calibration-output", str(calibration_output),
            "--output", str(cycle_output),
        ]
    ) == 0

    payload = json.loads(cycle_output.read_text(encoding="utf-8"))
    assert payload["status"] == "partial_gates_not_met"
    assert payload["run"]["completed_cases"] == 4
    assert payload["calibration"]["status"] == "diagnosed"
    stdout = capsys.readouterr().out
    assert "status=partial_gates_not_met fresh=4/7" in stdout
    assert "noisy run output" not in stdout
    assert "noisy ready output" not in stdout
