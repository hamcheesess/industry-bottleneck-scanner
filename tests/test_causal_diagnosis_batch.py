from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.artifacts import (
    write_atomic_signals_jsonl,
    write_operating_support,
)
from industry_bottleneck_scanner.causal_diagnosis_batch import build_causal_diagnosis_batch
from industry_bottleneck_scanner.models import AtomicSignal, Classification
from industry_bottleneck_scanner.operating_support import (
    EvidenceTimingSummary,
    OperatingSupport,
)


AS_OF = datetime(2026, 8, 21, 23, 59, 59, tzinfo=timezone.utc)
BUCKET = "SIC 3420 — CUTLERY, HANDTOOLS & GENERAL HARDWARE"


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    market = tmp_path / "market.json"
    market.write_text(
        json.dumps(
            {
                "schema_version": "industry-market-trigger-v1",
                "as_of": "2026-08-21",
                "triggers": [
                    {
                        "bucket": BUCKET,
                        "company_count": 3,
                        "market_outperform_breadth": 1.0,
                        "sector_outperform_breadth": 1.0,
                        "near_high_breadth": 0.67,
                        "abnormal_volume_breadth": 0.67,
                        "median_market_relative_3m": 0.2,
                        "median_sector_relative_3m": 0.1,
                        "score": 82.0,
                        "triggered": True,
                        "reasons": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence"
    bucket_dir = evidence / "buckets" / "bucket-a"
    support = OperatingSupport(
        bucket=BUCKET,
        as_of=AS_OF,
        expected_company_ids=("issuer-a", "issuer-b", "issuer-c"),
        document_company_ids=("issuer-a", "issuer-b"),
        fresh_company_ids=("issuer-a", "issuer-b"),
        fresh_document_ids=("doc-a", "doc-b"),
        stale_document_ids=(),
        future_document_ids=(),
        active_signal_ids=("signal-a", "signal-b"),
        active_company_ids=("issuer-a", "issuer-b"),
        source_types=("sec_8k_exhibit",),
        timing=EvidenceTimingSummary(0, 0, 2, 0, 0),
        stage="one_sided_strengthening",
        reasons=("multi_company_one_sided_strengthening",),
    )
    write_operating_support(bucket_dir / "operating_support.json", support)
    signals = (
        AtomicSignal(
            signal_id="signal-a",
            scanner="demand",
            metric="backlog_strength",
            direction="strengthening",
            magnitude="unknown",
            company_id="issuer-a",
            ticker="AAA",
            classification=Classification(industry=BUCKET),
            subject=None,
            document_id="doc-a",
            document_type="sec_8k_exhibit",
            published_at=AS_OF,
            source_url="https://www.sec.gov/a",
            evidence_text="Record backlog.",
            negated=False,
            resolved=False,
            extraction_method="keyword",
            confidence=0.9,
        ),
        AtomicSignal(
            signal_id="signal-b",
            scanner="scarcity",
            metric="capacity_constraint",
            direction="strengthening",
            magnitude="unknown",
            company_id="issuer-b",
            ticker="BBB",
            classification=Classification(industry=BUCKET),
            subject=None,
            document_id="doc-b",
            document_type="sec_8k_exhibit",
            published_at=AS_OF,
            source_url="https://www.sec.gov/b",
            evidence_text="Capacity remains constrained.",
            negated=False,
            resolved=False,
            extraction_method="keyword",
            confidence=0.9,
        ),
    )
    write_atomic_signals_jsonl(bucket_dir / "atomic_signals.jsonl", signals)
    (evidence / "operating_evidence_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "operating-evidence-batch-v1",
                "as_of": AS_OF.isoformat(),
                "strict_as_of": True,
                "buckets": [{"bucket": BUCKET, "path": "buckets/bucket-a"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return market, evidence


def test_builds_mixed_diagnosis_and_fail_closed_root_shock_queue(tmp_path: Path) -> None:
    market, evidence = _inputs(tmp_path)
    output = tmp_path / "out"

    manifest = build_causal_diagnosis_batch(
        market_trigger_path=market,
        operating_evidence_dir=evidence,
        output_dir=output,
    )

    assert manifest["strict_as_of"] is True
    assert manifest["provider_specific_code_used"] is False
    assert manifest["classification_counts"]["mixed_or_early"] == 1
    diagnosis = manifest["diagnoses"][0]
    assert diagnosis["signal_families"] == ["demand", "scarcity"]
    queue = json.loads((output / "root_shock_research_queue.json").read_text())
    assert queue["candidate_count"] == 1
    assert queue["automatic_root_shock_approvals"] == 0
    candidate = queue["candidates"][0]
    assert candidate["approval_status"] == "research_required"
    assert "external_corroboration" in candidate["required_before_approval"]
    assert "economic_node_assignment" in candidate["required_before_approval"]


def test_rejects_market_and_operating_cutoff_mismatch(tmp_path: Path) -> None:
    market, evidence = _inputs(tmp_path)
    payload = json.loads(market.read_text())
    payload["as_of"] = "2026-08-20"
    market.write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="as_of dates do not match"):
        build_causal_diagnosis_batch(
            market_trigger_path=market,
            operating_evidence_dir=evidence,
            output_dir=tmp_path / "out",
        )


def test_rejects_future_document_references(tmp_path: Path) -> None:
    market, evidence = _inputs(tmp_path)
    support_path = evidence / "buckets" / "bucket-a" / "operating_support.json"
    payload = json.loads(support_path.read_text())
    payload["future_document_ids"] = ["future-doc"]
    support_path.write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="future document references"):
        build_causal_diagnosis_batch(
            market_trigger_path=market,
            operating_evidence_dir=evidence,
            output_dir=tmp_path / "out",
        )
