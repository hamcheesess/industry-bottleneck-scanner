from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

from .industry_state import FileIndustryStateRegistry
from .industry_state_updater import (
    IndustryStateObservation,
    decision_to_dict,
    evaluate_industry_state_update,
    observation_from_dict,
    observations_from_atomic_signals,
)
from .models import AtomicSignal, Classification


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must use ISO-8601") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def _jsonl(path: Path) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(payload)
    return tuple(rows)


def _atomic_signal(payload: dict[str, object]) -> AtomicSignal:
    classification = payload.get("classification") or {}
    if not isinstance(classification, dict):
        raise ValueError("AtomicSignal classification must be an object")
    return AtomicSignal(
        signal_id=str(payload["signal_id"]),
        scanner=str(payload["scanner"]),  # type: ignore[arg-type]
        metric=str(payload["metric"]),
        direction=str(payload["direction"]),  # type: ignore[arg-type]
        magnitude=str(payload["magnitude"]),  # type: ignore[arg-type]
        company_id=str(payload["company_id"]),
        ticker=None if payload.get("ticker") is None else str(payload["ticker"]),
        classification=Classification(
            sector=None if classification.get("sector") is None else str(classification["sector"]),
            industry=None if classification.get("industry") is None else str(classification["industry"]),
            subindustry=(
                None if classification.get("subindustry") is None else str(classification["subindustry"])
            ),
        ),
        subject=None if payload.get("subject") is None else str(payload["subject"]),
        document_id=str(payload["document_id"]),
        document_type=str(payload["document_type"]),
        published_at=datetime.fromisoformat(str(payload["published_at"])),
        source_url=None if payload.get("source_url") is None else str(payload["source_url"]),
        evidence_text=str(payload["evidence_text"]),
        negated=bool(payload["negated"]),
        resolved=bool(payload["resolved"]),
        extraction_method=str(payload["extraction_method"]),
        confidence=float(payload["confidence"]),
        matched_phrase=(
            None if payload.get("matched_phrase") is None else str(payload["matched_phrase"])
        ),
        comparison_basis=str(payload.get("comparison_basis") or "unspecified"),  # type: ignore[arg-type]
        source_section=(
            None if payload.get("source_section") is None else str(payload["source_section"])
        ),
        speaker=None if payload.get("speaker") is None else str(payload["speaker"]),
        speaker_title=(
            None if payload.get("speaker_title") is None else str(payload["speaker_title"])
        ),
    )


def _assignments(path: Path) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"company_id", "node_id"} <= set(reader.fieldnames or ()):
            raise ValueError("node assignments CSV requires company_id,node_id")
        values: dict[str, set[str]] = {}
        all_nodes: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            company_id = (row.get("company_id") or "").strip()
            node_id = (row.get("node_id") or "").strip()
            if not company_id or not node_id:
                raise ValueError(f"row {row_number}: company_id and node_id are required")
            values.setdefault(company_id, set()).add(node_id)
            all_nodes.add(node_id)
    return (
        {company_id: tuple(sorted(node_ids)) for company_id, node_ids in values.items()},
        tuple(sorted(all_nodes)),
    )


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate and append evidence-diverse economic-node state snapshots"
    )
    parser.add_argument("--observations-jsonl", type=Path)
    parser.add_argument("--atomic-signals-jsonl", type=Path)
    parser.add_argument("--node-assignments-csv", type=Path)
    parser.add_argument("--as-of", type=_timestamp, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.atomic_signals_jsonl is None) != (args.node_assignments_csv is None):
        raise SystemExit("--atomic-signals-jsonl and --node-assignments-csv must be provided together")
    if args.observations_jsonl is None and args.atomic_signals_jsonl is None:
        raise SystemExit("provide external observations or AtomicSignal plus node assignments")

    observations: list[IndustryStateObservation] = []
    node_ids: set[str] = set()
    if args.observations_jsonl is not None:
        external = tuple(observation_from_dict(row) for row in _jsonl(args.observations_jsonl))
        observations.extend(external)
        node_ids.update(item.node_id for item in external)
    if args.atomic_signals_jsonl is not None:
        assignments, assigned_nodes = _assignments(args.node_assignments_csv)
        node_ids.update(assigned_nodes)
        signals = tuple(_atomic_signal(row) for row in _jsonl(args.atomic_signals_jsonl))
        observations.extend(
            observations_from_atomic_signals(signals, company_node_assignments=assignments)
        )
    if not node_ids:
        raise SystemExit("no economic node IDs were supplied")

    registry = FileIndustryStateRegistry(args.registry)
    existing = registry.load()
    decisions = []
    for node_id in sorted(node_ids):
        if any(item.node_id == node_id and item.as_of == args.as_of for item in existing):
            raise SystemExit(f"snapshot already exists for {node_id} at {args.as_of.isoformat()}")
        previous_items = [
            item for item in existing if item.node_id == node_id and item.as_of < args.as_of
        ]
        previous = max(previous_items, key=lambda item: item.as_of) if previous_items else None
        decisions.append(
            evaluate_industry_state_update(
                node_id=node_id,
                as_of=args.as_of,
                observations=observations,
                previous=previous,
            )
        )

    for decision in decisions:
        if decision.approved:
            registry.append(decision.snapshot)
    _atomic_json(
        args.decisions,
        {
            "schema_version": "industry-state-update-batch-v1",
            "as_of": args.as_of.isoformat(),
            "node_count": len(decisions),
            "approved_count": sum(item.approved for item in decisions),
            "decisions": [decision_to_dict(item) for item in decisions],
        },
    )
    print(
        f"nodes={len(decisions)} approved={sum(item.approved for item in decisions)} "
        f"observations={len(observations)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
