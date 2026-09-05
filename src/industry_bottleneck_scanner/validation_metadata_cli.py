from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .transcript_collection import TranscriptRequest
from .transcript_store import FileTranscriptStore
from .universe import normalize_ticker
from .validation_metadata import choose_explicit_call_date


@dataclass(frozen=True)
class ClassificationDefaults:
    sector: str | None = None
    industry: str | None = None
    subindustry: str | None = None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create current/baseline metadata draft CSVs for a frozen validation request file. "
            "Publication timestamps remain blank until independently verified. Explicit dates "
            "found in cached transcript text are emitted only as research hints."
        )
    )
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--current-quarter", required=True)
    parser.add_argument("--baseline-quarter", required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--sector")
    parser.add_argument("--industry")
    parser.add_argument("--subindustry")
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--current-output", type=Path, required=True)
    parser.add_argument("--baseline-output", type=Path, required=True)
    parser.add_argument("--checklist-output", type=Path, required=True)
    return parser


def _quarter(value: str, name: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 6 or normalized[4] != "Q" or normalized[5] not in "1234":
        raise SystemExit(f"{name} must use YYYYQ# format")
    return normalized


def _load_requests(path: Path) -> tuple[TranscriptRequest, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"ticker", "quarter"}.issubset(set(reader.fieldnames or ())):
            raise SystemExit(f"{path}: request CSV requires ticker and quarter columns")
        return tuple(
            TranscriptRequest(
                ticker=(row.get("ticker") or ""),
                quarter=(row.get("quarter") or ""),
            )
            for row in reader
        )


def _load_selection(path: Path | None) -> dict[str, dict[str, str | None]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    companies = payload.get("companies") if isinstance(payload, dict) else None
    if not isinstance(companies, list):
        raise SystemExit(f"{path}: selection JSON must contain a companies list")
    result: dict[str, dict[str, str | None]] = {}
    for item in companies:
        if not isinstance(item, dict):
            continue
        ticker = normalize_ticker(str(item.get("ticker") or ""))
        if not ticker:
            continue
        result[ticker] = {
            "company_id": str(item.get("company_id") or f"ticker-{ticker}"),
            "sector": str(item.get("sector") or "") or None,
            "industry": str(item.get("industry") or "") or None,
            "subindustry": str(item.get("subindustry") or "") or None,
        }
    return result


def _row_for(
    request: TranscriptRequest,
    *,
    selection: dict[str, dict[str, str | None]],
    defaults: ClassificationDefaults,
    store: FileTranscriptStore,
    provider: str,
) -> dict[str, str]:
    selected = selection.get(request.ticker, {})
    transcript = store.load(provider=provider, ticker=request.ticker, quarter=request.quarter)
    date_hint = choose_explicit_call_date(transcript) if transcript is not None else None
    source_url = transcript.source_url if transcript is not None and transcript.source_url else ""
    return {
        "ticker": request.ticker,
        "company_id": str(selected.get("company_id") or f"ticker-{request.ticker}"),
        "quarter": request.quarter,
        "published_at": "",
        "sector": str(selected.get("sector") or defaults.sector or ""),
        "industry": str(selected.get("industry") or defaults.industry or ""),
        "subindustry": str(selected.get("subindustry") or defaults.subindustry or ""),
        "published_at_source_url": source_url,
        "published_date_candidate": date_hint.value.isoformat() if date_hint else "",
        "published_date_evidence": date_hint.evidence_text if date_hint else "",
        "metadata_status": "needs_verified_timestamp",
    }


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "company_id",
        "quarter",
        "published_at",
        "sector",
        "industry",
        "subindustry",
        "published_at_source_url",
        "published_date_candidate",
        "published_date_evidence",
        "metadata_status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    current_quarter = _quarter(args.current_quarter, "--current-quarter")
    baseline_quarter = _quarter(args.baseline_quarter, "--baseline-quarter")
    if current_quarter == baseline_quarter:
        raise SystemExit("current and baseline quarters must differ")

    requests = _load_requests(args.requests)
    allowed = {current_quarter, baseline_quarter}
    unexpected = sorted({item.quarter for item in requests} - allowed)
    if unexpected:
        raise SystemExit(f"request file contains quarters outside current/baseline pair: {unexpected}")

    selection = _load_selection(args.selection)
    defaults = ClassificationDefaults(
        sector=(args.sector or "").strip() or None,
        industry=(args.industry or "").strip() or None,
        subindustry=(args.subindustry or "").strip() or None,
    )
    store = FileTranscriptStore(args.transcript_root)
    rows = [
        _row_for(
            request,
            selection=selection,
            defaults=defaults,
            store=store,
            provider=args.provider,
        )
        for request in requests
    ]
    current_rows = [row for row in rows if row["quarter"] == current_quarter]
    baseline_rows = [row for row in rows if row["quarter"] == baseline_quarter]
    _write_rows(args.current_output, current_rows)
    _write_rows(args.baseline_output, baseline_rows)
    _write_rows(args.checklist_output, rows)

    cached = sum(
        store.load(provider=args.provider, ticker=item.ticker, quarter=item.quarter) is not None
        for item in requests
    )
    date_hints = sum(bool(row["published_date_candidate"]) for row in rows)
    print(
        f"status=draft_created requests={len(rows)} cached_transcripts={cached} "
        f"explicit_date_hints={date_hints} verified_timestamps=0"
    )
    print(f"wrote {args.current_output}")
    print(f"wrote {args.baseline_output}")
    print(f"wrote {args.checklist_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
