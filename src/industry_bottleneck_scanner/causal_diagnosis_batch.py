from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .causal_diagnosis import CausalDiagnosis, diagnose_market_trigger
from .market_trigger import IndustryMarketTrigger
from .operating_support import EvidenceTimingSummary, OperatingSupport


SCHEMA_VERSION = "causal-diagnosis-batch-v1"
QUEUE_SCHEMA_VERSION = "root-shock-research-queue-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _market_trigger(payload: dict[str, object]) -> IndustryMarketTrigger:
    return IndustryMarketTrigger(
        bucket=str(payload["bucket"]),
        company_count=int(payload["company_count"]),
        market_outperform_breadth=float(payload["market_outperform_breadth"]),
        sector_outperform_breadth=float(payload["sector_outperform_breadth"]),
        near_high_breadth=float(payload["near_high_breadth"]),
        abnormal_volume_breadth=float(payload["abnormal_volume_breadth"]),
        median_market_relative_3m=float(payload["median_market_relative_3m"]),
        median_sector_relative_3m=float(payload["median_sector_relative_3m"]),
        score=float(payload["score"]),
        triggered=bool(payload["triggered"]),
        reasons=tuple(str(item) for item in payload.get("reasons", [])),  # type: ignore[arg-type]
    )


def _support(payload: dict[str, object]) -> OperatingSupport:
    if payload.get("schema_version") != "operating-support-v1":
        raise ValueError("unsupported OperatingSupport schema")
    timing = payload.get("timing")
    if not isinstance(timing, dict):
        raise ValueError("OperatingSupport timing must be an object")
    return OperatingSupport(
        bucket=str(payload["bucket"]),
        as_of=datetime.fromisoformat(str(payload["as_of"])),
        expected_company_ids=tuple(str(item) for item in payload["expected_company_ids"]),  # type: ignore[arg-type]
        document_company_ids=tuple(str(item) for item in payload["document_company_ids"]),  # type: ignore[arg-type]
        fresh_company_ids=tuple(str(item) for item in payload["fresh_company_ids"]),  # type: ignore[arg-type]
        fresh_document_ids=tuple(str(item) for item in payload["fresh_document_ids"]),  # type: ignore[arg-type]
        stale_document_ids=tuple(str(item) for item in payload["stale_document_ids"]),  # type: ignore[arg-type]
        future_document_ids=tuple(str(item) for item in payload["future_document_ids"]),  # type: ignore[arg-type]
        active_signal_ids=tuple(str(item) for item in payload["active_signal_ids"]),  # type: ignore[arg-type]
        active_company_ids=tuple(str(item) for item in payload["active_company_ids"]),  # type: ignore[arg-type]
        source_types=tuple(str(item) for item in payload["source_types"]),  # type: ignore[arg-type]
        timing=EvidenceTimingSummary(
            pre_existing_documents=int(timing["pre_existing_documents"]),
            recent_update_documents=int(timing["recent_update_documents"]),
            trigger_era_documents=int(timing["trigger_era_documents"]),
            stale_documents=int(timing["stale_documents"]),
            future_documents=int(timing["future_documents"]),
        ),
        stage=str(payload["stage"]),  # type: ignore[arg-type]
        reasons=tuple(str(item) for item in payload["reasons"]),  # type: ignore[arg-type]
        comparable_acceleration=None,
    )


def _diagnosis_payload(item: CausalDiagnosis) -> dict[str, object]:
    return asdict(item)


def build_causal_diagnosis_batch(
    *,
    market_trigger_path: Path,
    operating_evidence_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    market_payload = json.loads(market_trigger_path.read_text(encoding="utf-8"))
    if market_payload.get("schema_version") != "industry-market-trigger-v1":
        raise ValueError("unsupported market-trigger schema")
    market_as_of = str(market_payload["as_of"])

    operating_manifest_path = operating_evidence_dir / "operating_evidence_manifest.json"
    operating_manifest = json.loads(operating_manifest_path.read_text(encoding="utf-8"))
    if operating_manifest.get("schema_version") != "operating-evidence-batch-v1":
        raise ValueError("unsupported operating-evidence manifest schema")
    operating_as_of = datetime.fromisoformat(str(operating_manifest["as_of"]))
    if operating_as_of.date().isoformat() != market_as_of:
        raise ValueError("market and operating evidence as_of dates do not match")
    if not operating_manifest.get("strict_as_of"):
        raise ValueError("operating evidence must be strict-as-of")

    markets = {
        item.bucket: item
        for item in (
            _market_trigger(raw)
            for raw in market_payload.get("triggers", [])
            if isinstance(raw, dict)
        )
    }
    operating_rows = operating_manifest.get("buckets")
    if not isinstance(operating_rows, list):
        raise ValueError("operating-evidence manifest buckets must be a list")

    diagnoses: list[dict[str, object]] = []
    queue: list[dict[str, object]] = []
    for row in operating_rows:
        if not isinstance(row, dict):
            raise ValueError("operating-evidence bucket row must be an object")
        bucket = str(row["bucket"])
        market = markets.get(bucket)
        if market is None:
            raise ValueError(f"operating bucket absent from market-trigger artifact: {bucket}")
        bucket_dir = operating_evidence_dir / str(row["path"])
        support_payload = json.loads((bucket_dir / "operating_support.json").read_text())
        support = _support(support_payload)
        if support.bucket != bucket or support.as_of != operating_as_of:
            raise ValueError(f"OperatingSupport identity mismatch for {bucket}")
        if support.future_document_ids:
            raise ValueError(f"future document references are forbidden for {bucket}")
        diagnosis = diagnose_market_trigger(market, support=support)

        active_ids = set(support.active_signal_ids)
        signal_families: set[str] = set()
        signal_metrics: set[str] = set()
        for line in (bucket_dir / "atomic_signals.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            signal = json.loads(line)
            if signal.get("signal_id") in active_ids:
                signal_families.add(str(signal["scanner"]))
                signal_metrics.add(str(signal["metric"]))

        diagnosis_row = {
            **_diagnosis_payload(diagnosis),
            "market_score": market.score,
            "market_trigger_id": f"market-trigger:{market_as_of}:{hashlib.sha256(bucket.encode()).hexdigest()[:16]}",
            "active_company_count": len(support.active_company_ids),
            "active_signal_count": len(support.active_signal_ids),
            "signal_families": sorted(signal_families),
            "signal_metrics": sorted(signal_metrics),
            "operating_support_path": str((bucket_dir / "operating_support.json").relative_to(operating_evidence_dir)),
        }
        diagnoses.append(diagnosis_row)

        if diagnosis.classification in {"structural_operating", "mixed_or_early"}:
            queue.append(
                {
                    "bucket": bucket,
                    "market_trigger_id": diagnosis_row["market_trigger_id"],
                    "market_score": market.score,
                    "diagnosis": diagnosis.classification,
                    "operating_stage": diagnosis.operating_stage,
                    "fresh_coverage_ratio": support.fresh_coverage_ratio,
                    "active_company_count": len(support.active_company_ids),
                    "signal_families": sorted(signal_families),
                    "signal_metrics": sorted(signal_metrics),
                    "approval_status": "research_required",
                    "automatic_root_shock_approval": False,
                    "required_before_approval": [
                        "concrete_root_demand_mechanism",
                        "economic_node_assignment",
                        "second_independent_evidence_class",
                        "external_corroboration",
                    ],
                }
            )

    diagnoses.sort(key=lambda item: (-float(item["market_score"]), str(item["bucket"])))
    queue.sort(
        key=lambda item: (
            -len(item["signal_families"]),  # type: ignore[arg-type]
            -int(item["active_company_count"]),
            -float(item["market_score"]),
            str(item["bucket"]),
        )
    )
    diagnosis_manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": operating_as_of.isoformat(),
        "strict_as_of": True,
        "provider_specific_code_used": False,
        "market_trigger_source": str(market_trigger_path),
        "market_trigger_sha256": _sha256(market_trigger_path),
        "operating_evidence_manifest": str(operating_manifest_path),
        "operating_evidence_manifest_sha256": _sha256(operating_manifest_path),
        "diagnosis_count": len(diagnoses),
        "classification_counts": {
            name: sum(item["classification"] == name for item in diagnoses)
            for name in ("structural_operating", "narrative_led", "mixed_or_early", "unresolved")
        },
        "diagnoses": diagnoses,
    }
    queue_manifest: dict[str, object] = {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "as_of": operating_as_of.isoformat(),
        "candidate_count": len(queue),
        "automatic_root_shock_approvals": 0,
        "market_trigger_thresholds_changed": False,
        "candidates": queue,
    }
    _atomic_json(output_dir / "causal_diagnosis.json", diagnosis_manifest)
    _atomic_json(output_dir / "root_shock_research_queue.json", queue_manifest)
    return diagnosis_manifest
