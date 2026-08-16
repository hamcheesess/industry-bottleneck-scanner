import json
from pathlib import Path

from industry_bottleneck_scanner.validation_evidence_audit_cli import audit_result


def _signal(company: str, metric: str, *, evidence: str) -> dict[str, object]:
    return {
        "company_id": company,
        "ticker": company,
        "scanner": "demand" if metric == "backlog_strength" else "scarcity",
        "metric": metric,
        "direction": "strengthening",
        "negated": False,
        "resolved": False,
        "classification": {"sector": "Information Technology", "industry": None, "subindustry": None},
        "evidence_text": evidence,
        "extraction_method": "keyword",
        "matched_phrase": metric,
        "confidence": 0.9,
        "source_section": "qa",
        "speaker": "CEO",
        "speaker_title": "Chief Executive Officer",
        "document_id": f"doc-{company}-{metric}",
        "published_at": "2019-04-01T09:00:00-04:00",
        "source_url": "https://example.com/call",
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_audit_result_exposes_new_company_evidence_for_gain(tmp_path: Path) -> None:
    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    _write_jsonl(
        current_path,
        [
            _signal("AAA", "backlog_strength", evidence="Backlog increased."),
            _signal("BBB", "backlog_strength", evidence="Backlog grew."),
            _signal("CCC", "lead_time_pressure", evidence="Lead times extended."),
        ],
    )
    _write_jsonl(
        baseline_path,
        [_signal("AAA", "backlog_strength", evidence="Backlog increased.")],
    )
    payload = {
        "aggregation_level": "sector",
        "artifacts": {
            "current_signals_jsonl": str(current_path),
            "baseline_signals_jsonl": str(baseline_path),
        },
        "acceleration": [
            {
                "bucket": "Information Technology",
                "triggered": True,
                "confirmed": False,
                "watchlisted": False,
                "metric_prevalence_gains": ["backlog_strength", "lead_time_pressure"],
            }
        ],
    }

    report = audit_result(payload, limit=10)
    cluster = report["clusters"][0]
    backlog = next(item for item in cluster["metrics"] if item["metric"] == "backlog_strength")
    lead_time = next(item for item in cluster["metrics"] if item["metric"] == "lead_time_pressure")

    assert backlog["current_companies"] == ["AAA", "BBB"]
    assert backlog["baseline_companies"] == ["AAA"]
    assert backlog["new_supporting_companies"] == ["BBB"]
    assert lead_time["new_supporting_companies"] == ["CCC"]
    assert lead_time["current_evidence"][0]["evidence_text"] == "Lead times extended."
