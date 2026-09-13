import json
from pathlib import Path

from industry_bottleneck_scanner import validation_v1_closure_cli


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_closes_source_limited_v1_without_fallback(tmp_path: Path, capsys) -> None:
    collection = tmp_path / "collection.json"
    ready = tmp_path / "ready.json"
    calibration = tmp_path / "calibration.json"
    policy = tmp_path / "policy.json"
    output = tmp_path / "review.json"

    _write(
        collection,
        {
            "missing_requests": [
                {"ticker": "MDGL", "quarter": "2026Q2"},
                {"ticker": "REZI", "quarter": "2026Q2"},
            ],
            "run": {
                "rate_limited": 0,
                "errors": 0,
                "items": [
                    {"ticker": "MDGL", "quarter": "2026Q2", "status": "missing"},
                    {"ticker": "REZI", "quarter": "2026Q2", "status": "missing"},
                ],
            },
        },
    )
    _write(
        ready,
        {
            "status": "partial_waiting_data",
            "full_validation_complete": False,
            "total_frozen_cases": 7,
            "ready_case_ids": ["a", "b", "c", "d", "e", "f"],
            "summary": {
                "positive_stage_recall": 2 / 3,
                "expected_metric_recall": 6 / 7,
                "control_false_positive_rate": 1 / 3,
            },
        },
    )
    _write(
        calibration,
        {
            "cases": [
                {
                    "case_id": "auto-2019q2-control",
                    "role": "control",
                    "triggered_clusters": [{"bucket": "Consumer Discretionary"}],
                }
            ]
        },
    )
    _write(
        policy,
        {
            "policy_id": "frozen-v1-alpha-vantage-only",
            "provider": "alpha_vantage",
            "fallback_provider_allowed": False,
        },
    )

    assert validation_v1_closure_cli.main(
        [
            "--collection", str(collection),
            "--ready", str(ready),
            "--calibration", str(calibration),
            "--policy", str(policy),
            "--output", str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "closed_source_coverage_limited"
    assert payload["phase2_ready"] is False
    assert payload["next_gate"] == "v2_validation_contract_design"
    assert payload["provider_missing_requests"] == ["MDGL:2026Q2", "REZI:2026Q2"]
    assert payload["false_positive_control_case_ids"] == ["auto-2019q2-control"]
    stdout = capsys.readouterr().out
    assert "status=closed_source_coverage_limited" in stdout
    assert "phase2_ready=false" in stdout


def test_refuses_fallback_enabled_policy(tmp_path: Path) -> None:
    for name, value in (
        ("collection.json", {"missing_requests": [], "run": {}}),
        ("ready.json", {"full_validation_complete": False}),
        ("calibration.json", {"cases": []}),
    ):
        _write(tmp_path / name, value)
    _write(
        tmp_path / "policy.json",
        {
            "policy_id": "frozen-v1-alpha-vantage-only",
            "provider": "alpha_vantage",
            "fallback_provider_allowed": True,
        },
    )

    try:
        validation_v1_closure_cli.main(
            [
                "--collection", str(tmp_path / "collection.json"),
                "--ready", str(tmp_path / "ready.json"),
                "--calibration", str(tmp_path / "calibration.json"),
                "--policy", str(tmp_path / "policy.json"),
                "--output", str(tmp_path / "out.json"),
            ]
        )
    except SystemExit as exc:
        assert "fallback provider" in str(exc)
    else:
        raise AssertionError("fallback-enabled frozen v1 policy must fail closed")
