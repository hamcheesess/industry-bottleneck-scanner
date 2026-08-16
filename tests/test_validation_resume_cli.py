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
                    "missing_requests": [{"ticker": "ZZZ", "quarter": "2026Q2"}],
                    "run": {
                        "provider_requests": 3,
                        "fetched": 2,
                        "missing": 0,
                        "rate_limited": 1,
                        "errors": 0,
                        "items": [
                            {"ticker": "AAA", "quarter": "2026Q2", "status": "cache_hit"},
                            {"ticker": "BBB", "quarter": "2026Q2", "status": "fetched"},
                            {"ticker": "CCC", "quarter": "2026Q2", "status": "rate_limited"},
                        ],
                    },
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
                    "false_positive_control_case_ids": ["control-b"],
                    "freshness_and_validation": {
                        "total_frozen_cases": 7,
                        "ready_case_ids": ["a", "b", "c"],
                        "blocked_input_case_ids": ["e", "f", "g"],
                        "blocked_coverage_case_ids": ["d"],
                        "case_freshness": {},
                        "summary": {
                            "positive_stage_recall": 1.0,
                            "expected_metric_recall": 0.8,
                            "control_false_positive_rate": 1.0,
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
    assert payload["collection_stop"] == {
        "provider_requests": 3,
        "fetched": 2,
        "missing": 0,
        "rate_limited": 1,
        "errors": 0,
        "budget_exhausted": 0,
        "provider_missing_requests": [],
        "provider_error_requests": [],
        "reused_terminal_collection": False,
    }
    stdout = capsys.readouterr().out
    assert "status=partial_waiting_data" in stdout
    assert "next_action=provider_quota_resume_later" in stdout
    assert "provider_requests=3 fetched=2 missing=0 errors=0 rate_limited=1 budget_exhausted=0" in stdout
    assert "false_positive_controls=control-b" in stdout
    assert "collector detail" not in stdout


def test_resume_reports_local_budget_exhaustion_without_calling_it_rate_limit(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_collection(argv):
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps(
                {
                    "planned_unique_requests": 70,
                    "available_after_run": 56,
                    "remaining_after_run": 14,
                    "missing_requests": [{"ticker": "ZZZ", "quarter": "2026Q2"}],
                    "run": {
                        "provider_requests": 24,
                        "fetched": 22,
                        "missing": 0,
                        "rate_limited": 0,
                        "errors": 2,
                        "items": [{"ticker": "ZZZ", "quarter": "2026Q2", "status": "budget_exhausted"} for _ in range(14)],
                    },
                }
            ),
            encoding="utf-8",
        )
        return 2

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
                    "false_positive_control_case_ids": ["control-c"],
                    "freshness_and_validation": {
                        "total_frozen_cases": 7,
                        "ready_case_ids": ["a", "b", "c", "d", "e", "f"],
                        "blocked_input_case_ids": ["blind-proxy-2026"],
                        "blocked_coverage_case_ids": [],
                        "case_freshness": {"blind-proxy-2026": {"state": "blocked_inputs", "detail": "metadata missing"}},
                        "summary": {
                            "positive_stage_recall": 2 / 3,
                            "expected_metric_recall": 6 / 7,
                            "control_false_positive_rate": 1 / 3,
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
    assert payload["next_action"] == "provider_data_completion"
    assert payload["collection_stop"]["budget_exhausted"] == 14
    assert payload["collection_stop"]["rate_limited"] == 0
    stdout = capsys.readouterr().out
    assert "provider_requests=24 fetched=22 missing=0 errors=2 rate_limited=0 budget_exhausted=14" in stdout
    assert "false_positive_controls=control-c" in stdout


def test_resume_reuses_terminal_provider_missing_state_without_reissuing_requests(monkeypatch, tmp_path: Path, capsys) -> None:
    collection_output = tmp_path / "collection.json"
    collection_output.write_text(
        json.dumps(
            {
                "planned_unique_requests": 70,
                "available_after_run": 68,
                "remaining_after_run": 2,
                "missing_requests": [
                    {"ticker": "AAA", "quarter": "2026Q2"},
                    {"ticker": "BBB", "quarter": "2026Q1"},
                ],
                "run": {
                    "provider_requests": 14,
                    "fetched": 12,
                    "missing": 2,
                    "rate_limited": 0,
                    "errors": 0,
                    "items": [
                        {"ticker": "AAA", "quarter": "2026Q2", "status": "missing"},
                        {"ticker": "BBB", "quarter": "2026Q1", "status": "missing"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    def fail_collection(argv):  # pragma: no cover - must not be called
        raise AssertionError("terminal provider misses must not be retried automatically")

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
                    "false_positive_control_case_ids": ["auto-2019q2-control"],
                    "freshness_and_validation": {
                        "total_frozen_cases": 7,
                        "ready_case_ids": ["a", "b", "c", "d", "e", "f"],
                        "blocked_input_case_ids": ["blind-proxy-2026"],
                        "blocked_coverage_case_ids": [],
                        "case_freshness": {"blind-proxy-2026": {"state": "blocked_inputs", "detail": "metadata missing"}},
                        "summary": {
                            "positive_stage_recall": 2 / 3,
                            "expected_metric_recall": 6 / 7,
                            "control_false_positive_rate": 1 / 3,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(validation_resume_cli, "collection_main", fail_collection)
    monkeypatch.setattr(validation_resume_cli, "progress_main", fake_progress)
    monkeypatch.setattr(validation_resume_cli, "advance_main", fake_advance)
    monkeypatch.setattr(validation_resume_cli, "cycle_main", fake_cycle)

    output = tmp_path / "resume.json"
    assert validation_resume_cli.main(
        [
            "--collection-output", str(collection_output),
            "--progress-output", str(tmp_path / "progress.json"),
            "--advance-output", str(tmp_path / "advance.json"),
            "--cycle-output", str(tmp_path / "cycle.json"),
            "--output", str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["next_action"] == "provider_missing_transcripts_review"
    assert payload["collection_stop"]["reused_terminal_collection"] is True
    assert payload["collection_stop"]["provider_missing_requests"] == ["AAA:2026Q2", "BBB:2026Q1"]
    stdout = capsys.readouterr().out
    assert "provider_missing=AAA:2026Q2,BBB:2026Q1" in stdout
    assert "reused_terminal_collection=true" in stdout


def test_resume_surfaces_blind_timestamp_provenance_after_collection_completes(monkeypatch, tmp_path: Path) -> None:
    def fake_collection(argv):
        Path(argv[argv.index("--output") + 1]).write_text(
            json.dumps(
                {
                    "planned_unique_requests": 70,
                    "available_after_run": 70,
                    "remaining_after_run": 0,
                    "missing_requests": [],
                    "run": {"provider_requests": 0, "fetched": 0, "missing": 0, "rate_limited": 0, "errors": 0, "items": []},
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
                    "false_positive_control_case_ids": [],
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
