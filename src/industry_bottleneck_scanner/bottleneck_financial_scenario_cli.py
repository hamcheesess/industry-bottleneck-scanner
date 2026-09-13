from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bottleneck_financial_scenario import (
    build_bottleneck_financial_scenario,
    write_bottleneck_financial_scenario,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build strict-as-of 6/12/18 month bottleneck financial scenarios"
    )
    result.add_argument("--input", type=Path, required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scenario input must be an object")
    output = build_bottleneck_financial_scenario(payload)
    json_path, csv_path = write_bottleneck_financial_scenario(args.output_dir, output)
    decision = output["investment_research_decision"]
    readiness = output["readiness"]
    print(
        f"scenario_run_id={output['scenario_run_id']} candidate_id={output['candidate_id']} "
        f"readiness={readiness['status']} decision={decision['status']} "
        f"json={json_path} csv={csv_path}"
    )


if __name__ == "__main__":
    main()
