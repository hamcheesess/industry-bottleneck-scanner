import json
from pathlib import Path

from industry_bottleneck_scanner import validation_cli


def _fake_ready(*, complete: bool, gates_ok: bool):
    def run(argv):
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "status": "complete_pass" if complete and gates_ok else "partial_gates_ok",
                    "full_validation_complete": complete,
                    "provisional_gate_ok": gates_ok,
                    "ready_case_ids": ["a", "b", "c"] if not complete else ["a", "b", "c", "d"],
                    "total_frozen_cases": 4,
                    "summary": {
                        "positive_recall": 1.0,
                        "positive_stage_recall": 1.0,
                        "expected_metric_recall": 1.0,
                        "control_false_positive_rate": 0.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        return 0

    return run


def test_final_validation_cannot_pass_partial_fresh_manifest(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "validation.json"
    manifest = tmp_path / "cases.csv"
    manifest.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setattr(validation_cli, "ready_main", _fake_ready(complete=False, gates_ok=True))

    assert validation_cli.main(["--manifest", str(manifest), "--output", str(output)]) == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "needs_more_validation"
    assert payload["mode"] == "complete_frozen_manifest"


def test_final_validation_passes_only_complete_fresh_manifest(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "validation.json"
    manifest = tmp_path / "cases.csv"
    manifest.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setattr(validation_cli, "ready_main", _fake_ready(complete=True, gates_ok=True))

    assert validation_cli.main(["--manifest", str(manifest), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
