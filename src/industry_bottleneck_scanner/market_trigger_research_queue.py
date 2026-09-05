from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path


QUEUE_SCHEMA_VERSION = "market-trigger-research-queue-v1"
CSV_FIELDS = (
    "company_id",
    "issuer_id",
    "cik",
    "ticker",
    "company_name",
    "sector",
    "industry",
    "research_tier",
    "current_consecutive_run",
    "triggered_date_count",
    "latest_trigger_score",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def build_persistent_research_queue(
    quality_review_path: Path,
    universe_csv_path: Path,
    *,
    output_dir: Path,
    batch_size: int = 100,
) -> dict[str, object]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    review = json.loads(quality_review_path.read_text(encoding="utf-8"))
    if review.get("schema_version") != "market-trigger-quality-review-v1":
        raise ValueError("unsupported market-trigger quality review schema_version")
    if review.get("review_mode") != "outcome_blind_market_data_only":
        raise ValueError("research queue requires an outcome-blind quality review")
    if review.get("promotion_status") != "research_queue_ready":
        raise ValueError("market-trigger quality review is not research-queue ready")
    if review.get("policy_decision") != "frozen_no_threshold_change":
        raise ValueError("market-trigger thresholds must remain frozen")

    stability_rows = review.get("latest_bucket_stability", [])
    persistent = {
        str(item["bucket"]): item
        for item in stability_rows
        if item.get("research_tier") == "persistent"
    }
    if not persistent:
        raise ValueError("quality review contains no persistent buckets")

    with universe_csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"issuer_id", "cik", "ticker", "company_name", "sector", "bucket"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"universe CSV missing required columns: {sorted(missing)}")
        universe_rows = list(reader)

    selected: list[dict[str, object]] = []
    missing_cik_tickers: list[str] = []
    duplicate_security_tickers: list[str] = []
    bucket_counts = {bucket: 0 for bucket in persistent}
    seen_company_ids: set[str] = set()
    for row in universe_rows:
        bucket = (row.get("bucket") or "").strip()
        if bucket not in persistent:
            continue
        ticker = (row.get("ticker") or "").strip()
        cik = (row.get("cik") or "").strip()
        issuer_id = (row.get("issuer_id") or "").strip()
        company_id = issuer_id or (f"cik-{cik}" if cik else "")
        if not cik:
            missing_cik_tickers.append(ticker)
            continue
        if not company_id:
            raise ValueError(f"persistent issuer {ticker!r} has no stable company_id")
        if company_id in seen_company_ids:
            duplicate_security_tickers.append(ticker)
            continue
        stability = persistent[bucket]
        selected.append(
            {
                "company_id": company_id,
                "issuer_id": issuer_id,
                "cik": cik,
                "ticker": ticker,
                "company_name": (row.get("company_name") or "").strip(),
                "sector": (row.get("sector") or "").strip(),
                "industry": bucket,
                "research_tier": "persistent",
                "current_consecutive_run": int(stability["current_consecutive_run"]),
                "triggered_date_count": int(stability["triggered_date_count"]),
                "latest_trigger_score": float(stability["latest_score"]),
            }
        )
        bucket_counts[bucket] += 1
        seen_company_ids.add(company_id)

    empty_buckets = sorted(bucket for bucket, count in bucket_counts.items() if count == 0)
    if empty_buckets:
        raise ValueError(f"persistent buckets absent from universe CSV: {empty_buckets}")
    selected.sort(
        key=lambda row: (
            -int(row["current_consecutive_run"]),
            -int(row["triggered_date_count"]),
            -float(row["latest_trigger_score"]),
            str(row["industry"]),
            str(row["ticker"]),
        )
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    batch_rows = [selected[index : index + batch_size] for index in range(0, len(selected), batch_size)]
    batch_payloads: list[dict[str, object]] = []
    for index, rows in enumerate(batch_rows, start=1):
        path = output_dir / f"sec_issuers_batch_{index:03d}.csv"
        temporary = path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
        batch_payloads.append(
            {
                "batch": index,
                "path": path.name,
                "issuer_count": len(rows),
                "sha256": _sha256(path),
            }
        )

    manifest_path = output_dir / "research_queue_manifest.json"
    payload: dict[str, object] = {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "selection_mode": "latest_persistent_buckets_all_issuers",
        "outcome_data_used": False,
        "thresholds_changed": False,
        "provider_calls": 0,
        "quality_review": str(quality_review_path),
        "quality_review_sha256": _sha256(quality_review_path),
        "universe_csv": str(universe_csv_path),
        "universe_csv_sha256": _sha256(universe_csv_path),
        "universe_as_of": review["universe"]["as_of"],
        "market_as_of": review["archive_as_of"],
        "persistent_bucket_count": len(persistent),
        "selected_issuer_count": len(selected),
        "missing_cik_tickers": sorted(missing_cik_tickers),
        "duplicate_security_tickers": sorted(duplicate_security_tickers),
        "batch_size": batch_size,
        "batches": batch_payloads,
        "bucket_issuer_counts": dict(sorted(bucket_counts.items())),
    }
    _atomic_json(manifest_path, payload)
    return payload
