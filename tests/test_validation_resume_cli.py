import json
from pathlib import Path

from industry_bottleneck_scanner import validation_resume_cli


def test_resume_continues_after_bounded_incomplete_collection(monkeypatch, tmp_path: Path, capsys) -> None:
    collection_output = tmp_path / "collection.json"
    progress_output = tmp_path / "progress.json"
    advance_output = tmp_path / "advance.json"
    cycle_output = tmp_path / "cycle.json"
    resume_output = tmp_path / "resume.json"
    calls: list[str] = []

    def fake_collection(argv):
        calls.append("collection")
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "planned_unique_requests": 70,
                    "available_after_run": 35,
                    "remaining_after_run": 35,
                    "run": {"rate_limited": True},
                }
            ),
            encoding="utf-8",
        )
        print("collector detail that resume suppresses")
        return 2

    def fake_progress(argv):
        calls.append("progress")
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps({"status": "progressed", "metadata_drafted_cases": 3}), encoding="utf-8"
        )
        return 0

    def fake_advance(argv):
        calls.append("advance")
        assert "--skip-run" in argv
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps({"status": "finalized_only", "finalized_cases": ["a", "b", "c"]}), encoding="utf-8"
        )
        return 0

    def fake_cycle(argv):
        calls.append("cycle")
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps(
                {
                    "status": "partial_waiting_data",
                    "next_gate": "data_completion",
                    "freshness_and_validation": {
                        "total_frozen_cases": 7,
                        "ready_case_ids": ["a", "b", "c"],
                        "blocked_input_case_ids": ["e", "f", "g"],
                        "blocked_coverage_case_ids": ["d"],
                        "case_freshness": {},
                        "summary": {
                            "positive_stage_recall": 1.0,
                            "expected_metric_recall": 0.8,
                            "control_false_positive_rate": 0.0,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(validation_resume_cli, "collection_main", fake_collection)
    monkeypatch.setattr(validation_resume_cli, "progress_main", fake_progress)
    monkeypatch.setattr(validation_resume_cli, "advance_main", fake_advance)
    monkeypatch.setattr(validation_resume_cli, "cycle_main", fake_cycle)

    assert validation_resume_cli.main(
        [
            "--collection-output", str(collection_output),
            "--progress-output", str(progress_output),
            "--advance-output", str(advance_output),
            "--cycle-output", str(cycle_output),
            "--output", str(resume_output),
        ]
    ) == 0

    assert calls == ["collection", "progress", "advance", "cycle"]
    payload = json.loads(resume_output.read_text(encoding="utf-8"))
    assert payload["collection_exit_code"] == 2
    assert payload["next_gate"] == "data_completion"
    assert payload["next_action"] == "provider_quota_resume_later"
    stdout = capsys.readouterr().out
    assert "status=partial_waiting_data" in stdout
    assert "next_action=provider_quota_resume_later" in stdout
    assert "collector detail" not in stdout


def test_resume_surfaces_blind_timestamp_provenance_after_collection_completes(monkeypatch, tmp_path: Path) -> None:
    def fake_collection(argv):
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps(
                {
                    "planned_unique_requests": 70,
                    "available_after_run": 70,
                    "remaining_after_run": 0,
                    "run": {"rate_limited": False},
                }
            ),
            encoding="utf-8",
        )
        return 0

    def fake_progress(argv):
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps({"status": "progressed"}), encoding="utf-8")
        return 0

    def fake_advance(argv):
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps({"status": "finalized_only"}), encoding="utf-8")
        return 0

    def fake_cycle(argv):
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps(
                {
                    "status": "partial_waiting_data",
                    "next_gate": "data_completion",
                    "freshness_and_validation": {
                        "total_frozen_cases": 7,
                        "ready_case_ids": ["a", "b", "c", "d", "e", "f"],
                        "blocked_input_case_ids": ["blind-proxy-2026"],
                        "blocked_coverage_case_ids": [],
                        "case_freshness": {
                            "blind-proxy-2026": {
                                "state": "blocked_inputs",
                                "detail": "current metadata is not validation-ready: published_at is required",
                            }
                        },
                        "summary": {},
                    },
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(validation_resume_cli, "collection_main", fake_collection)
    monkeypatch.setattr(validation_resume_cli, "progress_main", fake_progress)
    monkeypatch.setattr(validation_resume_cli, "advance_main", fake_advance)
    monkeypatch.setattr(validation_resume_cli, "cycle_main", fake_cycle)

    output = tmp_path / "resume.json"
    assert validation_resume_cli.main(
        [
            "--collection-output", str(tmp_path / "collection.json"),
            "--progress-output", str(tmp_path / "progress.json"),
            "--advance-output", str(tmp_path / "advance.json"),
            "--cycle-output", str(tmp_path / "cycle.json"),
            "--output", str(output),
        ]
    ) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["next_action"] == "blind_timestamp_provenance"
