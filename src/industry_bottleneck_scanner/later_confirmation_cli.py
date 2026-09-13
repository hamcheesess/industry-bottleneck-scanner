from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .later_confirmation import build_diagnostic, write_diagnostic_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze and evaluate later-confirmation holdouts without reranking"
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--replay-result", type=Path, required=True)
    parser.add_argument("--evaluation-as-of", required=True)
    parser.add_argument("--evidence-package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _object(path: Path, name: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{name} must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    evidence_package = (
        None
        if args.evidence_package is None
        else _object(args.evidence_package, "evidence package")
    )
    diagnostic = build_diagnostic(
        _object(args.plan, "later-confirmation plan"),
        _object(args.replay_result, "replay result"),
        evaluation_as_of=datetime.fromisoformat(args.evaluation_as_of),
        evidence_package=evidence_package,
    )
    json_path, markdown_path = write_diagnostic_artifacts(args.output_dir, diagnostic)
    print(
        f"plan_id={diagnostic['plan_id']} node={diagnostic['node_id']} "
        f"status={diagnostic['node_diagnostic_status']} rerank=false "
        f"json={json_path} markdown={markdown_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
