import json
from pathlib import Path

from industry_bottleneck_scanner.validation_positive_audit_cli import main


def test_positive_audit_separates_metric_miss_from_stage_blocker(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("experiments").mkdir()
    Path("var/validation/artifacts/positive-a").mkdir(parents=True)
    Path("var/validation/artifacts/positive-b").mkdir(parents=True)
    Path("var/validation").mkdir(exist_ok=True)

    Path("experiments/phase1_validation_cases.csv").write_text(
        "case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes\n"
        "positive-a,positive,var/validation/positive-a.json,sector,Information Technology,capacity_constraint|backlog_strength,https://example.test/a,a\n"
        "positive-b,positive,var/validation/positive-b.json,industry,Electrical Equipment,backlog_strength,https://example.test/b,b\n",
        encoding="utf-8",
    )
    Path("var/validation/positive-a.json").write_text(
        json.dumps(
            {
                "aggregation_level": "sector",
                "acceleration": [
                    {
                        "bucket": "Information Technology",
                        "confirmed": True,
                        "triggered": True,
                        "watchlisted": False,
                        "watch_blockers": [],
                        "change_reasons": ["metric_prevalence_gain"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    Path("var/validation/positive-b.json").write_text(
        json.dumps(
            {
                "aggregation_level": "industry",
                "acceleration": [
                    {
                        "bucket": "Electrical Equipment",
                        "confirmed": False,
                        "triggered": False,
                        "watchlisted": False,
                        "watch_blockers": ["demand_scarcity_core_pair"],
                        "change_reasons": ["metric_prevalence_gain"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    Path("var/validation/artifacts/positive-a/current_signals.jsonl").write_text(
        json.dumps(
            {
                "ticker": "AAA",
                "company_id": "issuer-a",
                "metric": "capacity_constraint",
                "direction": "strengthening",
                "negated": False,
                "resolved": False,
                "classification": {"sector": "Information Technology"},
                "evidence_text": "Capacity constrained.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    Path("var/validation/artifacts/positive-b/current_signals.jsonl").write_text(
        json.dumps(
            {
                "ticker": "BBB",
                "company_id": "issuer-b",
                "metric": "backlog_strength",
                "direction": "strengthening",
                "negated": False,
                "resolved": False,
                "classification": {"industry": "Electrical Equipment"},
                "evidence_text": "Record backlog.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "status=positive_audited completed=2 failed=2" in output
    assert "positive_failure case=positive-a stage=confirmed missing_metrics=backlog_strength" in output
    assert "metric_failure case=positive-a metric=backlog_strength diagnosis=no_extracted_support" in output
    assert "positive_failure case=positive-b stage=observing missing_metrics=none stage_blockers=demand_scarcity_core_pair" in output

    payload = json.loads(Path("var/validation/positive-audit.json").read_text(encoding="utf-8"))
    assert payload["failed_positive_cases"] == 2
    first = next(item for item in payload["cases"] if item["case_id"] == "positive-a")
    assert first["missing_expected_metrics"] == ["backlog_strength"]
    second = next(item for item in payload["cases"] if item["case_id"] == "positive-b")
    assert second["stage_blockers"] == ["demand_scarcity_core_pair"]
