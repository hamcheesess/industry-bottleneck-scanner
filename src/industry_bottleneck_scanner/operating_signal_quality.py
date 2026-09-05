from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


SCHEMA_VERSION = "operating-signal-quality-v1"

SPECULATIVE_RISK_MARKERS = (
    "could adversely affect",
    "may adversely affect",
    "could have a material adverse",
    "may have a material adverse",
    "risks related to",
    "the possibility of",
    "our ability to",
    "the company’s ability to",
    "the company's ability to",
    "ability to obtain",
    "could decrease if",
    "may be further limited",
)


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _is_speculative_risk(text: str) -> bool:
    normalized = _normalize(text)
    return any(marker in normalized for marker in SPECULATIVE_RISK_MARKERS)


def signal_quality_flags(
    signals: list[dict[str, object]],
) -> dict[str, tuple[str, ...]]:
    """Classify signal-level quality without changing the canonical signal artifact."""

    company_evidence_counts: Counter[tuple[str, str]] = Counter(
        (str(item["company_id"]), _normalize(str(item["evidence_text"])))
        for item in signals
    )
    flags_by_signal: dict[str, tuple[str, ...]] = {}
    for item in signals:
        evidence = str(item["evidence_text"])
        key = (str(item["company_id"]), _normalize(evidence))
        flags: list[str] = []
        if _is_speculative_risk(evidence):
            flags.append("speculative_risk_language")
        if company_evidence_counts[key] > 1:
            flags.append("repeated_company_evidence")
        flags_by_signal[str(item["signal_id"])] = tuple(flags)
    return flags_by_signal


def audit_operating_signal_quality(
    *,
    causal_diagnosis_dir: Path,
    operating_evidence_dir: Path,
    output_path: Path,
) -> dict[str, object]:
    queue_path = causal_diagnosis_dir / "root_shock_research_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("schema_version") != "root-shock-research-queue-v1":
        raise ValueError("unsupported root-shock research queue schema")
    operating_manifest = json.loads(
        (operating_evidence_dir / "operating_evidence_manifest.json").read_text(encoding="utf-8")
    )
    if operating_manifest.get("schema_version") != "operating-evidence-batch-v1":
        raise ValueError("unsupported operating-evidence manifest schema")
    if queue.get("as_of") != operating_manifest.get("as_of"):
        raise ValueError("causal diagnosis and operating evidence as_of do not match")
    bucket_paths = {
        str(item["bucket"]): operating_evidence_dir / str(item["path"])
        for item in operating_manifest.get("buckets", [])
        if isinstance(item, dict)
    }

    audits: list[dict[str, object]] = []
    for candidate in queue.get("candidates", []):
        if not isinstance(candidate, dict):
            raise ValueError("root-shock queue candidate must be an object")
        bucket = str(candidate["bucket"])
        bucket_dir = bucket_paths.get(bucket)
        if bucket_dir is None:
            raise ValueError(f"candidate bucket absent from operating evidence: {bucket}")
        support = json.loads((bucket_dir / "operating_support.json").read_text())
        active_ids = set(str(item) for item in support["active_signal_ids"])
        active: list[dict] = []
        for line in (bucket_dir / "atomic_signals.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            signal = json.loads(line)
            if signal.get("signal_id") in active_ids:
                active.append(signal)

        flags_by_signal = signal_quality_flags(active)
        direct: list[dict] = []
        for item in active:
            if not flags_by_signal[str(item["signal_id"])]:
                direct.append(item)

        direct_companies = sorted({str(item["company_id"]) for item in direct})
        direct_families = sorted({str(item["scanner"]) for item in direct})
        flagged_counts = Counter(flag for flags in flags_by_signal.values() for flag in flags)
        if len(direct_companies) >= 2 and len(direct_families) >= 2:
            status = "direct_multi_company"
        elif direct_companies:
            status = "sparse_direct"
        else:
            status = "boilerplate_dominated"
        examples_by_flag: dict[str, list[dict[str, object]]] = defaultdict(list)
        for item in active:
            for flag in flags_by_signal[str(item["signal_id"])]:
                if len(examples_by_flag[flag]) < 3:
                    evidence = str(item["evidence_text"])
                    examples_by_flag[flag].append(
                        {
                            "signal_id": item["signal_id"],
                            "company_id": item["company_id"],
                            "evidence_sha256": hashlib.sha256(
                                _normalize(evidence).encode("utf-8")
                            ).hexdigest(),
                            "excerpt": evidence[:240],
                        }
                    )
        audits.append(
            {
                "bucket": bucket,
                "market_score": candidate["market_score"],
                "quality_status": status,
                "active_signal_count": len(active),
                "direct_signal_count": len(direct),
                "direct_signal_ratio": round(len(direct) / len(active), 6) if active else 0.0,
                "active_company_count": len({str(item["company_id"]) for item in active}),
                "direct_company_count": len(direct_companies),
                "direct_signal_families": direct_families,
                "flag_counts": dict(sorted(flagged_counts.items())),
                "flag_examples": dict(sorted(examples_by_flag.items())),
                "automatic_root_shock_approval": False,
            }
        )

    priority = {"direct_multi_company": 0, "sparse_direct": 1, "boilerplate_dominated": 2}
    audits.sort(
        key=lambda item: (
            priority[str(item["quality_status"])],
            -int(item["direct_company_count"]),
            -float(item["market_score"]),
            str(item["bucket"]),
        )
    )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": queue["as_of"],
        "audit_is_signal_mutation": False,
        "automatic_root_shock_approvals": 0,
        "candidate_count": len(audits),
        "quality_status_counts": {
            name: sum(item["quality_status"] == name for item in audits)
            for name in ("direct_multi_company", "sparse_direct", "boilerplate_dominated")
        },
        "candidates": audits,
    }
    _atomic_json(output_path, payload)
    return payload
