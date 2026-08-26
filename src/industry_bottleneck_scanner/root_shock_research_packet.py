from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from .operating_signal_quality import signal_quality_flags


SCHEMA_VERSION = "root-shock-research-packet-v1"
MANIFEST_SCHEMA_VERSION = "root-shock-research-packet-manifest-v1"
EXCERPT_LIMIT = 480
REQUIRED_BEFORE_APPROVAL = {
    "concrete_root_demand_mechanism",
    "economic_node_assignment",
    "second_independent_evidence_class",
    "external_corroboration",
}


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


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _aware_datetime(value: object, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return parsed


def _candidate_id(*, as_of: str, market_trigger_id: str, bucket: str) -> str:
    raw = f"{as_of}|{market_trigger_id}|{bucket}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _latest_first(signals: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        signals,
        key=lambda item: (
            _aware_datetime(item["published_at"], field="signal published_at"),
            str(item["signal_id"]),
        ),
        reverse=True,
    )


def _select_diverse_signals(
    signals: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("max evidence per candidate must be positive")
    ordered = _latest_first(signals)
    selected: list[dict[str, object]] = []
    selected_ids: set[str] = set()
    selected_companies: set[str] = set()

    def add(item: dict[str, object]) -> None:
        signal_id = str(item["signal_id"])
        if signal_id in selected_ids or len(selected) >= limit:
            return
        selected.append(item)
        selected_ids.add(signal_id)
        selected_companies.add(str(item["company_id"]))

    for dimension in ("scanner", "metric"):
        values = sorted({str(item[dimension]) for item in ordered})
        for value in values:
            match = next(
                (
                    item
                    for item in ordered
                    if str(item[dimension]) == value
                    and str(item["signal_id"]) not in selected_ids
                    and str(item["company_id"]) not in selected_companies
                ),
                None,
            )
            if match is not None:
                add(match)
            if len(selected) >= limit:
                return selected

    for item in ordered:
        if str(item["company_id"]) not in selected_companies:
            add(item)
        if len(selected) >= limit:
            return selected
    for item in ordered:
        add(item)
        if len(selected) >= limit:
            break
    return selected


def _evidence_row(signal: dict[str, object]) -> dict[str, object]:
    evidence = " ".join(str(signal["evidence_text"]).split())
    return {
        "signal_id": signal["signal_id"],
        "company_id": signal["company_id"],
        "ticker": signal.get("ticker"),
        "scanner": signal["scanner"],
        "metric": signal["metric"],
        "direction": signal.get("direction"),
        "document_id": signal["document_id"],
        "document_type": signal["document_type"],
        "published_at": signal["published_at"],
        "source_url": signal["source_url"],
        "source_section": signal.get("source_section"),
        "source_category": "issuer_operating_disclosure",
        "evidence_sha256": hashlib.sha256(evidence.casefold().encode("utf-8")).hexdigest(),
        "excerpt": evidence[:EXCERPT_LIMIT],
    }


def build_root_shock_research_packets(
    *,
    causal_diagnosis_dir: Path,
    operating_evidence_dir: Path,
    quality_audit_path: Path,
    output_dir: Path,
    max_evidence_per_candidate: int = 12,
) -> dict[str, object]:
    """Create bounded provider-free research inputs while keeping approval fail-closed."""

    queue_path = causal_diagnosis_dir / "root_shock_research_queue.json"
    queue = _load_object(queue_path)
    if queue.get("schema_version") != "root-shock-research-queue-v1":
        raise ValueError("unsupported root-shock research queue schema")
    quality = _load_object(quality_audit_path)
    if quality.get("schema_version") != "operating-signal-quality-v1":
        raise ValueError("unsupported operating-signal quality schema")
    if queue.get("automatic_root_shock_approvals") != 0:
        raise ValueError("research queue must not contain automatic root-shock approvals")
    if quality.get("automatic_root_shock_approvals") != 0:
        raise ValueError("quality audit must not contain automatic root-shock approvals")
    if quality.get("audit_is_signal_mutation") is not False:
        raise ValueError("quality audit must be a non-mutating view")
    operating_manifest_path = operating_evidence_dir / "operating_evidence_manifest.json"
    operating_manifest = _load_object(operating_manifest_path)
    if operating_manifest.get("schema_version") != "operating-evidence-batch-v1":
        raise ValueError("unsupported operating-evidence manifest schema")
    if not operating_manifest.get("strict_as_of"):
        raise ValueError("operating evidence must be strict-as-of")

    as_of_text = str(queue["as_of"])
    if quality.get("as_of") != as_of_text or operating_manifest.get("as_of") != as_of_text:
        raise ValueError("research queue, quality audit, and operating evidence as_of must match")
    as_of = _aware_datetime(as_of_text, field="research as_of")

    queue_candidates = {
        str(item["bucket"]): item
        for item in queue.get("candidates", [])
        if isinstance(item, dict)
    }
    quality_candidates = {
        str(item["bucket"]): item
        for item in quality.get("candidates", [])
        if isinstance(item, dict)
    }
    if not queue_candidates or set(queue_candidates) != set(quality_candidates):
        raise ValueError("research queue and quality audit candidate sets must match")
    if int(queue.get("candidate_count", -1)) != len(queue_candidates):
        raise ValueError("research queue candidate count is inconsistent")
    if int(quality.get("candidate_count", -1)) != len(quality_candidates):
        raise ValueError("quality audit candidate count is inconsistent")

    bucket_paths = {
        str(item["bucket"]): operating_evidence_dir / str(item["path"])
        for item in operating_manifest.get("buckets", [])
        if isinstance(item, dict)
    }
    packet_index: list[dict[str, object]] = []
    ordered_quality = [
        item for item in quality.get("candidates", []) if isinstance(item, dict)
    ]
    for priority, quality_row in enumerate(ordered_quality, start=1):
        bucket = str(quality_row["bucket"])
        candidate = queue_candidates[bucket]
        if candidate.get("automatic_root_shock_approval") is not False:
            raise ValueError(f"candidate must remain fail-closed before research: {bucket}")
        requirements = {str(item) for item in candidate.get("required_before_approval", [])}
        if not REQUIRED_BEFORE_APPROVAL.issubset(requirements):
            raise ValueError(f"candidate approval requirements are incomplete for {bucket}")
        bucket_dir = bucket_paths.get(bucket)
        if bucket_dir is None:
            raise ValueError(f"candidate bucket absent from operating evidence: {bucket}")
        support = _load_object(bucket_dir / "operating_support.json")
        active_ids = {str(item) for item in support.get("active_signal_ids", [])}
        active: list[dict[str, object]] = []
        for line in (bucket_dir / "atomic_signals.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            signal = json.loads(line)
            if not isinstance(signal, dict):
                raise ValueError(f"{bucket}: signal row must be an object")
            if str(signal.get("signal_id")) not in active_ids:
                continue
            published_at = _aware_datetime(signal["published_at"], field="signal published_at")
            if published_at > as_of:
                raise ValueError(f"look-ahead signal is forbidden for {bucket}: {signal['signal_id']}")
            active.append(signal)
        if len(active) != len(active_ids):
            raise ValueError(f"active signal references are incomplete for {bucket}")

        flags = signal_quality_flags(active)
        direct = [item for item in active if not flags[str(item["signal_id"])]]
        direct_companies = {str(item["company_id"]) for item in direct}
        direct_families = {str(item["scanner"]) for item in direct}
        if int(quality_row["direct_signal_count"]) != len(direct):
            raise ValueError(f"quality audit direct signal count mismatch for {bucket}")
        if int(quality_row["direct_company_count"]) != len(direct_companies):
            raise ValueError(f"quality audit direct company count mismatch for {bucket}")
        if set(str(item) for item in quality_row["direct_signal_families"]) != direct_families:
            raise ValueError(f"quality audit signal family mismatch for {bucket}")

        selected = _select_diverse_signals(direct, limit=max_evidence_per_candidate)
        market_trigger_id = str(candidate["market_trigger_id"])
        packet_id = _candidate_id(
            as_of=as_of_text,
            market_trigger_id=market_trigger_id,
            bucket=bucket,
        )
        relative_path = Path("candidates") / f"{packet_id}.json"
        packet: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "priority": priority,
            "as_of": as_of_text,
            "strict_as_of": True,
            "provider_specific_code_used": False,
            "bucket": bucket,
            "market_trigger_id": market_trigger_id,
            "market_score": candidate["market_score"],
            "diagnosis": candidate["diagnosis"],
            "quality_status": quality_row["quality_status"],
            "research_status": "awaiting_external_research",
            "approval_ready": False,
            "automatic_root_shock_approval": False,
            "known_source_categories": ["issuer_operating_disclosure"],
            "missing_requirements": sorted(requirements),
            "research_questions": [
                "What concrete exogenous demand mechanism explains the dated market trigger?",
                "Which stable economic node receives that demand before issuer mapping?",
                "What independent evidence class from a non-issuer source existed by as_of?",
                "Which external source corroborates the mechanism without post-cutoff leakage?",
            ],
            "selected_direct_evidence_count": len(selected),
            "selected_company_count": len({str(item["company_id"]) for item in selected}),
            "selected_signal_families": sorted({str(item["scanner"]) for item in selected}),
            "direct_evidence": [_evidence_row(item) for item in selected],
            "adjudication_template": {
                "root_shock_id": None,
                "mechanism": None,
                "root_node_id": None,
                "independent_evidence": [],
                "external_corroboration": [],
                "decision": "research_required",
            },
        }
        _atomic_json(output_dir / relative_path, packet)
        packet_index.append(
            {
                "priority": priority,
                "packet_id": packet_id,
                "path": str(relative_path),
                "bucket": bucket,
                "market_trigger_id": market_trigger_id,
                "quality_status": quality_row["quality_status"],
                "selected_direct_evidence_count": len(selected),
                "approval_ready": False,
            }
        )

    manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "as_of": as_of_text,
        "strict_as_of": True,
        "provider_specific_code_used": False,
        "automatic_root_shock_approvals": 0,
        "approval_ready_count": 0,
        "candidate_count": len(packet_index),
        "max_evidence_per_candidate": max_evidence_per_candidate,
        "selection_policy": [
            "exclude_speculative_risk_language",
            "exclude_repeated_same_company_evidence",
            "prefer_scanner_diversity",
            "prefer_metric_diversity",
            "prefer_source_entity_diversity",
            "prefer_recent_pre_cutoff_evidence",
        ],
        "inputs": {
            "root_shock_research_queue": str(queue_path),
            "root_shock_research_queue_sha256": _sha256(queue_path),
            "operating_evidence_manifest": str(operating_manifest_path),
            "operating_evidence_manifest_sha256": _sha256(operating_manifest_path),
            "quality_audit": str(quality_audit_path),
            "quality_audit_sha256": _sha256(quality_audit_path),
        },
        "candidates": packet_index,
    }
    _atomic_json(output_dir / "research_packet_manifest.json", manifest)
    return manifest
