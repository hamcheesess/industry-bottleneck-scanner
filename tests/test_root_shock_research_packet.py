from __future__ import annotations

import json
from pathlib import Path

import pytest

from industry_bottleneck_scanner.operating_signal_quality import audit_operating_signal_quality
from industry_bottleneck_scanner.root_shock_research_packet import (
    build_root_shock_research_packets,
)
from industry_bottleneck_scanner.root_shock_research_packet_cli import main


AS_OF = "2026-08-21T23:59:59+00:00"
BUCKET = "SIC 3560 — GENERAL INDUSTRIAL MACHINERY & EQUIPMENT"


def _signal(
    signal_id: str,
    company_id: str,
    scanner: str,
    metric: str,
    evidence: str,
    *,
    published_at: str,
) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "company_id": company_id,
        "ticker": company_id.upper(),
        "scanner": scanner,
        "metric": metric,
        "direction": "strengthening",
        "document_id": f"document-{signal_id}",
        "document_type": "sec_10q",
        "published_at": published_at,
        "source_url": f"https://www.sec.gov/Archives/{signal_id}.htm",
        "source_section": "section-1",
        "evidence_text": evidence,
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    diagnosis = tmp_path / "diagnosis"
    diagnosis.mkdir()
    queue = {
        "schema_version": "root-shock-research-queue-v1",
        "as_of": AS_OF,
        "candidate_count": 1,
        "automatic_root_shock_approvals": 0,
        "candidates": [
            {
                "bucket": BUCKET,
                "market_trigger_id": "market-trigger:2026-08-21:machinery",
                "market_score": 78.0,
                "diagnosis": "mixed_or_early",
                "automatic_root_shock_approval": False,
                "required_before_approval": [
                    "concrete_root_demand_mechanism",
                    "economic_node_assignment",
                    "second_independent_evidence_class",
                    "external_corroboration",
                ],
            }
        ],
    }
    (diagnosis / "root_shock_research_queue.json").write_text(json.dumps(queue) + "\n")

    operating = tmp_path / "operating"
    bucket_dir = operating / "buckets" / "machinery"
    bucket_dir.mkdir(parents=True)
    signals = [
        _signal(
            "demand-a",
            "issuer-a",
            "demand",
            "backlog_strength",
            "Backlog increased to a record level on firm customer orders.",
            published_at="2026-08-01T12:00:00+00:00",
        ),
        _signal(
            "scarcity-b",
            "issuer-b",
            "scarcity",
            "capacity_constraint",
            "Current production capacity is fully allocated through year end.",
            published_at="2026-08-02T12:00:00+00:00",
        ),
        _signal(
            "pricing-c",
            "issuer-c",
            "pricing",
            "contract_repricing",
            "We repriced multi-year customer contracts during the quarter.",
            published_at="2026-08-03T12:00:00+00:00",
        ),
        _signal(
            "risk-d",
            "issuer-d",
            "capex",
            "capacity_expansion",
            "Supply shortages could adversely affect our future results.",
            published_at="2026-08-04T12:00:00+00:00",
        ),
    ]
    (bucket_dir / "atomic_signals.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in signals)
    )
    (bucket_dir / "operating_support.json").write_text(
        json.dumps({"active_signal_ids": [item["signal_id"] for item in signals]}) + "\n"
    )
    (operating / "operating_evidence_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "operating-evidence-batch-v1",
                "as_of": AS_OF,
                "strict_as_of": True,
                "buckets": [{"bucket": BUCKET, "path": "buckets/machinery"}],
            }
        )
        + "\n"
    )
    quality = diagnosis / "operating_signal_quality.json"
    audit_operating_signal_quality(
        causal_diagnosis_dir=diagnosis,
        operating_evidence_dir=operating,
        output_path=quality,
    )
    return diagnosis, operating, quality


def test_builds_bounded_diverse_fail_closed_packets(tmp_path: Path) -> None:
    diagnosis, operating, quality = _write_inputs(tmp_path)
    output = tmp_path / "research"
    manifest = build_root_shock_research_packets(
        causal_diagnosis_dir=diagnosis,
        operating_evidence_dir=operating,
        quality_audit_path=quality,
        output_dir=output,
        max_evidence_per_candidate=3,
    )

    assert manifest["strict_as_of"] is True
    assert manifest["candidate_count"] == 1
    assert manifest["automatic_root_shock_approvals"] == 0
    assert manifest["approval_ready_count"] == 0
    row = manifest["candidates"][0]
    packet = json.loads((output / row["path"]).read_text())
    assert packet["approval_ready"] is False
    assert packet["selected_direct_evidence_count"] == 3
    assert packet["selected_company_count"] == 3
    assert set(packet["selected_signal_families"]) == {"demand", "pricing", "scarcity"}
    assert {item["signal_id"] for item in packet["direct_evidence"]} == {
        "demand-a",
        "pricing-c",
        "scarcity-b",
    }
    assert packet["adjudication_template"]["decision"] == "research_required"
    assert manifest["inputs"]["quality_audit_sha256"]


def test_rejects_post_cutoff_signal(tmp_path: Path) -> None:
    diagnosis, operating, quality = _write_inputs(tmp_path)
    signal_path = operating / "buckets" / "machinery" / "atomic_signals.jsonl"
    rows = [json.loads(line) for line in signal_path.read_text().splitlines()]
    rows[0]["published_at"] = "2026-08-22T00:00:00+00:00"
    signal_path.write_text("".join(json.dumps(item) + "\n" for item in rows))

    with pytest.raises(ValueError, match="look-ahead signal"):
        build_root_shock_research_packets(
            causal_diagnosis_dir=diagnosis,
            operating_evidence_dir=operating,
            quality_audit_path=quality,
            output_dir=tmp_path / "research",
        )


def test_rejects_candidate_set_mismatch(tmp_path: Path) -> None:
    diagnosis, operating, quality = _write_inputs(tmp_path)
    payload = json.loads(quality.read_text())
    payload["candidates"][0]["bucket"] = "Different bucket"
    quality.write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="candidate sets must match"):
        build_root_shock_research_packets(
            causal_diagnosis_dir=diagnosis,
            operating_evidence_dir=operating,
            quality_audit_path=quality,
            output_dir=tmp_path / "research",
        )


def test_rejects_weakened_approval_requirements(tmp_path: Path) -> None:
    diagnosis, operating, quality = _write_inputs(tmp_path)
    queue_path = diagnosis / "root_shock_research_queue.json"
    payload = json.loads(queue_path.read_text())
    payload["candidates"][0]["required_before_approval"] = ["economic_node_assignment"]
    queue_path.write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="approval requirements are incomplete"):
        build_root_shock_research_packets(
            causal_diagnosis_dir=diagnosis,
            operating_evidence_dir=operating,
            quality_audit_path=quality,
            output_dir=tmp_path / "research",
        )


def test_cli_writes_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    diagnosis, operating, quality = _write_inputs(tmp_path)
    output = tmp_path / "research"
    assert (
        main(
            [
                "--causal-diagnosis-dir",
                str(diagnosis),
                "--operating-evidence-dir",
                str(operating),
                "--quality-audit",
                str(quality),
                "--output-dir",
                str(output),
                "--max-evidence-per-candidate",
                "2",
            ]
        )
        == 0
    )
    assert (output / "research_packet_manifest.json").exists()
    assert "automatic_root_shock_approvals=0" in capsys.readouterr().out
