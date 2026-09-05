from __future__ import annotations

import argparse
import json
from pathlib import Path

from .weekly_research_publish import build_weekly_site_export, write_weekly_site_artifacts


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Publish compact weekly industry statuses and final reports only"
    )
    result.add_argument("--input", type=Path, required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("weekly research input must be an object")
    site_export, feedback_export = build_weekly_site_export(payload)
    site_path, feedback_path = write_weekly_site_artifacts(
        args.output_dir, site_export, feedback_export
    )
    print(
        f"run_id={site_export['run_id']} candidates={site_export['summary']['candidate_count']} "
        f"rejected={site_export['summary']['rejected_count']} "
        f"final_reports={site_export['summary']['final_report_count']} "
        f"site={site_path} feedback={feedback_path}"
    )


if __name__ == "__main__":
    main()
