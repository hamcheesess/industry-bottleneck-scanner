from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply independently verified timezone-aware timestamps to Phase-1 metadata drafts. "
            "Every row must match ticker+quarter and carry an HTTP(S) provenance URL."
        )
    )
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _timestamp(value: str, *, row_number: int) -> str:
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"verified row {row_number}: published_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SystemExit(f"verified row {row_number}: published_at must include a timezone offset")
    return parsed.isoformat()


def _source_url(value: str, *, row_number: int) -> str:
    text = value.strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(f"verified row {row_number}: published_at_source_url must be HTTP(S)")
    return text


def _load_verified(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticker", "quarter", "published_at", "published_at_source_url"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(f"{path}: missing required columns {sorted(missing)}")
        result: dict[tuple[str, str], tuple[str, str]] = {}
        for row_number, row in enumerate(reader, start=2):
            ticker = (row.get("ticker") or "").strip().upper().replace(".", "-")
            quarter = (row.get("quarter") or "").strip().upper()
            if not ticker or not quarter:
                raise SystemExit(f"verified row {row_number}: ticker and quarter are required")
            key = (ticker, quarter)
            if key in result:
                raise SystemExit(f"verified row {row_number}: duplicate ticker/quarter {ticker} {quarter}")
            result[key] = (
                _timestamp(row.get("published_at") or "", row_number=row_number),
                _source_url(row.get("published_at_source_url") or "", row_number=row_number),
            )
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    verified = _load_verified(args.verified)

    with args.draft.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        required = {"ticker", "quarter", "published_at", "published_at_source_url"}
        missing = required - set(fieldnames)
        if missing:
            raise SystemExit(f"{args.draft}: missing required columns {sorted(missing)}")
        rows = list(reader)

    draft_keys = {
        ((row.get("ticker") or "").strip().upper().replace(".", "-"), (row.get("quarter") or "").strip().upper())
        for row in rows
    }
    missing_verified = sorted(draft_keys - set(verified))
    extra_verified = sorted(set(verified) - draft_keys)
    if missing_verified:
        raise SystemExit(f"verified timestamps missing draft rows: {missing_verified}")
    if extra_verified:
        raise SystemExit(f"verified timestamps contain rows absent from draft: {extra_verified}")

    for row in rows:
        key = (
            (row.get("ticker") or "").strip().upper().replace(".", "-"),
            (row.get("quarter") or "").strip().upper(),
        )
        timestamp, source_url = verified[key]
        row["published_at"] = timestamp
        row["published_at_source_url"] = source_url
        if "metadata_status" in fieldnames:
            row["metadata_status"] = "verified"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"status=finalized rows={len(rows)} verified={len(verified)}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
