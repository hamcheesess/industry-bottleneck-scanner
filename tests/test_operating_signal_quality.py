from __future__ import annotations

import json
from pathlib import Path

from industry_bottleneck_scanner.operating_signal_quality import audit_operating_signal_quality


BUCKET = "Electrical Equipment"
AS_OF = "2026-08-21T23:59:59+00:00"


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    diagnosis = tmp_path / "diagnosis"
    diagnosis.mkdir()
    (diagnosis / "root_shock_research_queue.json").write_text(
        json.dumps(
            {
                "schema_version": "root-shock-research-queue-v1",
                "as_of": AS_OF,
                "candidates": [{"bucket": BUCKET, "market_score": 80.0}],
            }
        )
        + "\n"
    )
    operating = tmp_path / "operating"
    bucket_dir = operating / "buckets" / "electrical"
    bucket_dir.mkdir(parents=True)
    (operating / "operating_evidence_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "operating-evidence-batch-v1",
                "as_of": AS_OF,
                "buckets": [{"bucket": BUCKET, "path": "buckets/electrical"}],
            }
        )
        + "\n"
    )
    signals = [
        {
            "signal_id": "risk-a",
            "company_id": "issuer-a",
            "scanner": "scarcity",
            "metric": "supply_tightness",
            "evidence_text": "Supply shortages could adversely affect our results.",
        },
        {
            "signal_id": "repeat-a-1",
            "company_id": "issuer-a",
            "scanner": "demand",
            "metric": "backlog_strength",
            "evidence_text": "Backlog reached a record level.",
        },
        {
            "signal_id": "repeat-a-2",
            "company_id": "issuer-a",
            "scanner": "demand",
            "metric": "backlog_strength",
            "evidence_text": "Backlog reached a record level.",
        },
        {
            "signal_id": "direct-b",
            "company_id": "issuer-b",
            "scanner": "scarcity",
            "metric": "capacity_constraint",
            "evidence_text": "Current production capacity is fully allocated.",
        },
        {
            "signal_id": "direct-c",
            "company_id": "issuer-c",
            "scanner": "pricing",
            "metric": "contract_repricing",
            "evidence_text": "We repriced customer contracts during the quarter.",
        },
    ]
    (bucket_dir / "atomic_signals.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in signals)
    )
    (bucket_dir / "operating_support.json").write_text(
        json.dumps({"active_signal_ids": [item["signal_id"] for item in signals]}) + "\n"
    )
    return diagnosis, operating


def test_audit_flags_speculative_and_repeated_evidence_without_mutating_signals(tmp_path: Path) -> None:
    diagnosis, operating = _write_inputs(tmp_path)
    payload = audit_operating_signal_quality(
        causal_diagnosis_dir=diagnosis,
        operating_evidence_dir=operating,
        output_path=tmp_path / "quality.json",
    )

    assert payload["audit_is_signal_mutation"] is False
    assert payload["automatic_root_shock_approvals"] == 0
    assert payload["quality_status_counts"]["direct_multi_company"] == 1
    candidate = payload["candidates"][0]
    assert candidate["direct_signal_count"] == 2
    assert candidate["direct_company_count"] == 2
    assert candidate["flag_counts"] == {
        "repeated_company_evidence": 2,
        "speculative_risk_language": 1,
    }


def test_audit_keeps_evidence_excerpts_bounded(tmp_path: Path) -> None:
    diagnosis, operating = _write_inputs(tmp_path)
    payload = audit_operating_signal_quality(
        causal_diagnosis_dir=diagnosis,
        operating_evidence_dir=operating,
        output_path=tmp_path / "quality.json",
    )
    examples = payload["candidates"][0]["flag_examples"]
    assert all(len(item["excerpt"]) <= 240 for rows in examples.values() for item in rows)
