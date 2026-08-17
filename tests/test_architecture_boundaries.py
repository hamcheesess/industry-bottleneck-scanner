from __future__ import annotations

import ast
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "industry_bottleneck_scanner"
REPO_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_CAUSAL_MODULES = (
    "market_history.py",
    "market_trigger.py",
    "causal_diagnosis.py",
    "causal_expansion.py",
    "causal_graph.py",
    "industry_state.py",
    "demand_convergence.py",
)

PARKED_PROVIDER_MODULES = {
    "quartr",
    "transcript_fallback",
    "v2_source_provenance",
}


def _local_import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and module:
                roots.add(module.split(".")[0])
            elif module.startswith("industry_bottleneck_scanner."):
                roots.add(module.split(".", 1)[1].split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("industry_bottleneck_scanner."):
                    roots.add(name.split(".", 1)[1].split(".")[0])
    return roots


def test_active_causal_modules_do_not_depend_on_parked_quartr_path() -> None:
    violations: dict[str, list[str]] = {}
    for name in ACTIVE_CAUSAL_MODULES:
        imports = _local_import_roots(PACKAGE_ROOT / name)
        bad = sorted(imports & PARKED_PROVIDER_MODULES)
        if bad:
            violations[name] = bad
    assert violations == {}


def test_active_policy_supersedes_transcript_v2_without_rewriting_frozen_v1() -> None:
    active = json.loads(
        (REPO_ROOT / "experiments" / "market_triggered_discovery_policy.draft.json").read_text(
            encoding="utf-8"
        )
    )
    legacy = json.loads(
        (REPO_ROOT / "experiments" / "v2_validation_policy.draft.json").read_text(
            encoding="utf-8"
        )
    )

    assert active["policy_id"] == "market-triggered-causal-discovery-v0"
    assert active["architecture"]["transcript_completeness_is_discovery_gate"] is False
    assert active["legacy_compatibility"]["frozen_v1"] == "frozen_audit_only"
    assert active["legacy_compatibility"]["quartr_availability_may_gate_active_architecture"] is False

    assert legacy["status"] == "superseded_historical_only"
    assert legacy["active_for_execution"] is False
    assert legacy["frozen_v1_rewritten"] is False
    assert legacy["superseded_by"] == active["policy_id"]


def test_current_roadmap_is_declared_source_of_truth() -> None:
    active = json.loads(
        (REPO_ROOT / "experiments" / "market_triggered_discovery_policy.draft.json").read_text(
            encoding="utf-8"
        )
    )
    roadmap = REPO_ROOT / active["architecture_source_of_truth"]
    compatibility = REPO_ROOT / active["compatibility_map"]
    assert roadmap.exists()
    assert compatibility.exists()
