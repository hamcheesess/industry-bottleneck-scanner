from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


QUALITY_SCHEMA_VERSION = "market-trigger-quality-review-v1"


@dataclass(frozen=True)
class DatedTriggerQuality:
    as_of: str
    assessed_bucket_count: int
    triggered_bucket_count: int
    trigger_rate: float
    previous_date_jaccard: float | None


@dataclass(frozen=True)
class LatestBucketStability:
    bucket: str
    latest_score: float
    latest_company_count: int
    triggered_date_count: int
    longest_consecutive_run: int
    current_consecutive_run: int
    first_triggered_as_of: str
    research_tier: str


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


def _longest_run(values: list[bool]) -> int:
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def _current_run(values: list[bool]) -> int:
    current = 0
    for value in reversed(values):
        if not value:
            break
        current += 1
    return current


def build_market_trigger_quality_review(
    calibration_dir: Path,
    *,
    output_path: Path,
) -> dict[str, object]:
    manifest_path = calibration_dir / "calibration_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "market-trigger-calibration-v1":
        raise ValueError("unsupported calibration manifest schema_version")
    if manifest.get("provider_calls") != 0:
        raise ValueError("quality review requires a provider-free calibration manifest")
    if manifest.get("policy_status") != "frozen_observation_only_no_threshold_tuning":
        raise ValueError("calibration policy must remain frozen before quality review")

    dated_rows = manifest.get("dates")
    if not isinstance(dated_rows, list) or not dated_rows:
        raise ValueError("calibration manifest must contain dated artifacts")

    artifacts: list[dict[str, object]] = []
    previous_as_of = ""
    for row in dated_rows:
        if not isinstance(row, dict):
            raise ValueError("invalid dated calibration row")
        artifact_path = calibration_dir / str(row["artifact_path"])
        if _sha256(artifact_path) != row.get("artifact_sha256"):
            raise ValueError(f"calibration artifact hash mismatch: {artifact_path}")
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        as_of = str(artifact.get("as_of") or "")
        if artifact.get("schema_version") != "industry-market-trigger-v1":
            raise ValueError("unsupported market-trigger artifact schema_version")
        if as_of != row.get("as_of") or as_of <= previous_as_of:
            raise ValueError("dated calibration artifacts must be strictly ordered")
        if artifact.get("policy") != manifest.get("policy"):
            raise ValueError("market-trigger policy changed inside calibration series")
        if artifact.get("universe", {}).get("as_of") != manifest.get("universe", {}).get("as_of"):
            raise ValueError("universe provenance changed inside calibration series")
        buckets = [str(item["bucket"]) for item in artifact.get("triggers", [])]
        if len(buckets) != len(set(buckets)):
            raise ValueError(f"{as_of}: duplicate market-trigger bucket")
        artifacts.append(artifact)
        previous_as_of = as_of

    date_sets: list[set[str]] = []
    timelines: dict[str, list[bool]] = {}
    dated_quality: list[DatedTriggerQuality] = []
    all_buckets = sorted(
        {
            str(item["bucket"])
            for artifact in artifacts
            for item in artifact.get("triggers", [])
        }
    )
    for bucket in all_buckets:
        timelines[bucket] = []

    for index, artifact in enumerate(artifacts):
        trigger_rows = artifact.get("triggers", [])
        triggered = {str(item["bucket"]) for item in trigger_rows if item.get("triggered") is True}
        date_sets.append(triggered)
        for bucket in all_buckets:
            timelines[bucket].append(bucket in triggered)
        previous = date_sets[index - 1] if index else None
        union = triggered | previous if previous is not None else set()
        jaccard = None if previous is None else (len(triggered & previous) / len(union) if union else 1.0)
        dated_quality.append(
            DatedTriggerQuality(
                as_of=str(artifact["as_of"]),
                assessed_bucket_count=len(trigger_rows),
                triggered_bucket_count=len(triggered),
                trigger_rate=round(len(triggered) / len(trigger_rows), 6) if trigger_rows else 0.0,
                previous_date_jaccard=None if jaccard is None else round(jaccard, 6),
            )
        )

    latest = artifacts[-1]
    latest_by_bucket = {str(item["bucket"]): item for item in latest.get("triggers", [])}
    latest_triggered = date_sets[-1]
    stability: list[LatestBucketStability] = []
    dates = [str(item["as_of"]) for item in artifacts]
    for bucket in latest_triggered:
        timeline = timelines[bucket]
        current_run = _current_run(timeline)
        first_index = timeline.index(True)
        row = latest_by_bucket[bucket]
        stability.append(
            LatestBucketStability(
                bucket=bucket,
                latest_score=float(row["score"]),
                latest_company_count=int(row["company_count"]),
                triggered_date_count=sum(timeline),
                longest_consecutive_run=_longest_run(timeline),
                current_consecutive_run=current_run,
                first_triggered_as_of=dates[first_index],
                research_tier="persistent" if current_run >= 2 else "emerging",
            )
        )
    stability.sort(
        key=lambda item: (
            item.research_tier == "persistent",
            item.current_consecutive_run,
            item.triggered_date_count,
            item.latest_score,
            item.latest_company_count,
            item.bucket,
        ),
        reverse=True,
    )

    persistent_count = sum(item.research_tier == "persistent" for item in stability)
    jaccards = [item.previous_date_jaccard for item in dated_quality if item.previous_date_jaccard is not None]
    payload: dict[str, object] = {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "review_mode": "outcome_blind_market_data_only",
        "promotion_status": "research_queue_ready" if stability else "no_latest_triggers",
        "policy_decision": "frozen_no_threshold_change",
        "provider_calls": 0,
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": _sha256(manifest_path),
        "universe": manifest["universe"],
        "archive_as_of": manifest["archive_as_of"],
        "calibration_window": manifest["calibration_window"],
        "policy": manifest["policy"],
        "summary": {
            "date_count": len(artifacts),
            "latest_triggered_bucket_count": len(latest_triggered),
            "latest_persistent_bucket_count": persistent_count,
            "latest_emerging_bucket_count": len(stability) - persistent_count,
            "mean_adjacent_jaccard": round(sum(jaccards) / len(jaccards), 6) if jaccards else None,
            "min_adjacent_jaccard": min(jaccards) if jaccards else None,
            "max_adjacent_jaccard": max(jaccards) if jaccards else None,
        },
        "dated_quality": [asdict(item) for item in dated_quality],
        "latest_bucket_stability": [asdict(item) for item in stability],
        "research_queue_rule": {
            "persistent": "triggered on the latest two or more consecutive calibration dates",
            "emerging": "triggered on the latest date but not the preceding date",
            "note": "classification only; trigger thresholds and historical cohort are unchanged",
        },
    }
    _atomic_json(output_path, payload)
    return payload
