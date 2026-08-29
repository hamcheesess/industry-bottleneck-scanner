from __future__ import annotations

import argparse
import json
from pathlib import Path

from .industry_analysis_report import (
    build_industry_analysis_report,
    file_sha256,
    write_industry_analysis_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a strict-as-of reader-facing industry analysis report"
    )
    parser.add_argument("--analysis-input", type=Path, required=True)
    parser.add_argument("--replay-result", type=Path, required=True)
    parser.add_argument("--replay-freeze", type=Path, required=True)
    parser.add_argument("--market-trigger-artifact", type=Path, required=True)
    parser.add_argument("--market-quality-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _object(path: Path, name: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{name} must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_industry_analysis_report(
        _object(args.analysis_input, "analysis input"),
        _object(args.replay_result, "replay result"),
        _object(args.replay_freeze, "replay freeze"),
        _object(args.market_trigger_artifact, "market-trigger artifact"),
        _object(args.market_quality_review, "market quality review"),
        analysis_input_sha256=file_sha256(args.analysis_input),
        market_trigger_artifact_sha256=file_sha256(args.market_trigger_artifact),
        market_quality_review_sha256=file_sha256(args.market_quality_review),
    )
    json_path, markdown_path = write_industry_analysis_artifacts(args.output_dir, report)
    print(
        f"report_id={report['report_id']} node_id={report['node_id']} "
        f"strict_as_of=true evidence={report['evidence_reference_count']} "
        f"json={json_path} markdown={markdown_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
