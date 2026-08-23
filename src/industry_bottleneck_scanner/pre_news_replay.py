from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .causal_expansion import CausalEvidence, NodeAssessment, RankedNode, rank_nodes
from .causal_orchestration import CausalConvergenceRun
from .demand_convergence import DemandConvergenceAssessment

REPLAY_INPUT_SCHEMA = "historical-pre-news-replay-input-v1"
REPLAY_FREEZE_SCHEMA = "historical-pre-news-replay-freeze-v1"
REPLAY_RESULT_SCHEMA = "historical-pre-news-replay-result-v1"

PROMOTED_CONVERGENCE_STAGES = {
    "pre_shock_bottleneck",
    "multi_branch_convergence",
    "priority_convergence",
}


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate_score(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")


def _required_score(payload: dict[str, object], name: str) -> int:
    value = payload[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer from 0 to 5")
    return value


@dataclass(frozen=True)
class PreNewsNodeJudgment:
    """Frozen research inputs that convergence/state logic cannot derive.

    Demand transmission is supplied by the approved causal path. The remaining scores stay
    explicit so the replay runner never invents economic-capture, reinvestment, triangulation,
    expectation-gap, or bottleneck judgments.
    """

    node_id: str
    bottleneck_strength: int
    economic_capture: int
    reinvestment_runway: int
    triangulation: int
    expectation_gap: int
    evidence: tuple[CausalEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        for name in (
            "bottleneck_strength",
            "economic_capture",
            "reinvestment_runway",
            "triangulation",
            "expectation_gap",
        ):
            _validate_score(name, getattr(self, name))


@dataclass(frozen=True)
class HistoricalReplaySpec:
    replay_id: str
    market_trigger_id: str
    trigger_root_shock_id: str
    as_of: datetime
    held_out_evidence_ids: tuple[str, ...]
    node_judgments: tuple[PreNewsNodeJudgment, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("replay_id", self.replay_id),
            ("market_trigger_id", self.market_trigger_id),
            ("trigger_root_shock_id", self.trigger_root_shock_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")
        _require_aware("as_of", self.as_of)
        if len(set(self.held_out_evidence_ids)) != len(self.held_out_evidence_ids):
            raise ValueError("held_out_evidence_ids must be unique")
        if any(not item.strip() for item in self.held_out_evidence_ids):
            raise ValueError("held_out_evidence_ids must not contain empty values")
        node_ids = [item.node_id for item in self.node_judgments]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("node judgments must have unique node_id values")


@dataclass(frozen=True)
class PreNewsReplayResult:
    replay_id: str
    as_of: datetime
    trigger_root_shock_id: str
    assessments: tuple[NodeAssessment, ...]
    ranked_nodes: tuple[RankedNode, ...]


def _unique_evidence(items: Iterable[CausalEvidence]) -> tuple[CausalEvidence, ...]:
    by_id: dict[str, CausalEvidence] = {}
    for item in items:
        existing = by_id.get(item.evidence_id)
        if existing is not None and existing != item:
            raise ValueError(f"conflicting causal evidence ID: {item.evidence_id}")
        by_id[item.evidence_id] = item
    return tuple(by_id[key] for key in sorted(by_id))


def _promoted_assessments(
    run: CausalConvergenceRun,
) -> tuple[DemandConvergenceAssessment, ...]:
    return tuple(
        item for item in run.assessments if item.stage in PROMOTED_CONVERGENCE_STAGES
    )


def run_pre_news_replay(
    run: CausalConvergenceRun,
    spec: HistoricalReplaySpec,
) -> PreNewsReplayResult:
    if run.trigger_root_shock_id != spec.trigger_root_shock_id:
        raise ValueError("replay trigger_root_shock_id does not match convergence run")
    if run.as_of != spec.as_of:
        raise ValueError("replay as_of must exactly match convergence run as_of")

    promoted = _promoted_assessments(run)
    if not promoted:
        raise ValueError("replay has no promoted convergence nodes")
    promoted_by_node = {item.node_id: item for item in promoted}
    judgments = {item.node_id: item for item in spec.node_judgments}
    missing = sorted(set(promoted_by_node) - set(judgments))
    unexpected = sorted(set(judgments) - set(promoted_by_node))
    if missing:
        raise ValueError("missing judgments for promoted nodes: " + ",".join(missing))
    if unexpected:
        raise ValueError("judgments supplied for non-promoted nodes: " + ",".join(unexpected))

    held_out = set(spec.held_out_evidence_ids)
    assessments: list[NodeAssessment] = []
    for node_id in sorted(promoted_by_node):
        convergence = promoted_by_node[node_id]
        judgment = judgments[node_id]
        state_evidence = (
            () if convergence.pre_shock_state is None else convergence.pre_shock_state.evidence
        )
        evidence = _unique_evidence(
            (
                *(item for branch in convergence.branches for item in branch.evidence),
                *state_evidence,
                *judgment.evidence,
            )
        )
        future = sorted(item.evidence_id for item in evidence if item.observed_at > spec.as_of)
        if future:
            raise ValueError("look-ahead evidence after replay as_of: " + ",".join(future))
        leaked_holdouts = sorted(item.evidence_id for item in evidence if item.evidence_id in held_out)
        if leaked_holdouts:
            raise ValueError("held-out evidence leaked into replay: " + ",".join(leaked_holdouts))

        assessments.append(
            NodeAssessment(
                node_id=node_id,
                as_of=spec.as_of,
                demand_transmission=convergence.trigger_transmission_strength,
                bottleneck_strength=judgment.bottleneck_strength,
                economic_capture=judgment.economic_capture,
                reinvestment_runway=judgment.reinvestment_runway,
                triangulation=judgment.triangulation,
                expectation_gap=judgment.expectation_gap,
                evidence=evidence,
            )
        )

    assessment_items = tuple(assessments)
    return PreNewsReplayResult(
        replay_id=spec.replay_id,
        as_of=spec.as_of,
        trigger_root_shock_id=spec.trigger_root_shock_id,
        assessments=assessment_items,
        ranked_nodes=rank_nodes(assessment_items),
    )


def _parse_evidence(payload: object) -> tuple[CausalEvidence, ...]:
    if not isinstance(payload, list):
        raise ValueError("node judgment evidence must be a list")
    evidence: list[CausalEvidence] = []
    for raw in payload:
        if not isinstance(raw, dict):
            raise ValueError("node judgment evidence rows must be objects")
        observed_at = datetime.fromisoformat(str(raw["observed_at"]))
        _require_aware("evidence observed_at", observed_at)
        evidence_id = str(raw["evidence_id"])
        source_id = str(raw["source_id"])
        summary = str(raw["summary"])
        if not evidence_id.strip() or not source_id.strip() or not summary.strip():
            raise ValueError("evidence_id, source_id, and summary are required")
        evidence.append(
            CausalEvidence(
                evidence_id=evidence_id,
                evidence_class=str(raw["evidence_class"]),  # type: ignore[arg-type]
                source_id=source_id,
                observed_at=observed_at,
                summary=summary,
                beneficiary_company_id=(
                    None
                    if raw.get("beneficiary_company_id") is None
                    else str(raw["beneficiary_company_id"])
                ),
                source_company_id=(
                    None
                    if raw.get("source_company_id") is None
                    else str(raw["source_company_id"])
                ),
            )
        )
    return tuple(evidence)


def replay_spec_from_dict(payload: dict[str, object]) -> HistoricalReplaySpec:
    if payload.get("schema_version") != REPLAY_INPUT_SCHEMA:
        raise ValueError("unsupported historical replay input schema")
    raw_judgments = payload.get("node_judgments")
    if not isinstance(raw_judgments, list):
        raise ValueError("node_judgments must be a list")
    judgments: list[PreNewsNodeJudgment] = []
    for raw in raw_judgments:
        if not isinstance(raw, dict):
            raise ValueError("node judgments must be objects")
        judgments.append(
            PreNewsNodeJudgment(
                node_id=str(raw["node_id"]),
                bottleneck_strength=_required_score(raw, "bottleneck_strength"),
                economic_capture=_required_score(raw, "economic_capture"),
                reinvestment_runway=_required_score(raw, "reinvestment_runway"),
                triangulation=_required_score(raw, "triangulation"),
                expectation_gap=_required_score(raw, "expectation_gap"),
                evidence=_parse_evidence(raw.get("evidence", [])),
            )
        )
    held_out = payload.get("held_out_evidence_ids", [])
    if not isinstance(held_out, list):
        raise ValueError("held_out_evidence_ids must be a list")
    return HistoricalReplaySpec(
        replay_id=str(payload["replay_id"]),
        market_trigger_id=str(payload["market_trigger_id"]),
        trigger_root_shock_id=str(payload["trigger_root_shock_id"]),
        as_of=datetime.fromisoformat(str(payload["as_of"])),
        held_out_evidence_ids=tuple(str(item) for item in held_out),
        node_judgments=tuple(judgments),
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence_reference(item: CausalEvidence) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "evidence_class": item.evidence_class,
        "source_id": item.source_id,
        "observed_at": item.observed_at.isoformat(),
    }


def build_replay_freeze(
    spec: HistoricalReplaySpec,
    *,
    trigger_detected_at: datetime,
    input_paths: dict[str, Path],
) -> dict[str, object]:
    _require_aware("trigger_detected_at", trigger_detected_at)
    if trigger_detected_at > spec.as_of:
        raise ValueError("trigger_detected_at cannot exceed replay as_of")
    fingerprints = {name: file_sha256(path) for name, path in sorted(input_paths.items())}
    payload: dict[str, object] = {
        "schema_version": REPLAY_FREEZE_SCHEMA,
        "replay_id": spec.replay_id,
        "market_trigger_id": spec.market_trigger_id,
        "trigger_root_shock_id": spec.trigger_root_shock_id,
        "trigger_detected_at": trigger_detected_at.isoformat(),
        "as_of": spec.as_of.isoformat(),
        "held_out_evidence_ids": list(spec.held_out_evidence_ids),
        "input_sha256": fingerprints,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["freeze_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def build_replay_result_artifact(
    result: PreNewsReplayResult,
    run: CausalConvergenceRun,
    freeze: dict[str, object],
) -> dict[str, object]:
    assessment_by_node = {item.node_id: item for item in result.assessments}
    convergence_by_node = {item.node_id: item for item in run.assessments}
    rankings: list[dict[str, object]] = []
    for ranked in result.ranked_nodes:
        assessment = assessment_by_node[ranked.node_id]
        convergence = convergence_by_node[ranked.node_id]
        rankings.append(
            {
                "node_id": ranked.node_id,
                "stage": ranked.stage,
                "score": ranked.score,
                "gate_reasons": list(ranked.gate_reasons),
                "evidence_classes": list(ranked.evidence_classes),
                "convergence_stage": convergence.stage,
                "convergence_score": convergence.score,
                "independent_root_shock_ids": list(
                    convergence.independent_root_shock_ids
                ),
                "pre_shock_state_as_of": (
                    None
                    if convergence.pre_shock_state is None
                    else convergence.pre_shock_state.as_of.isoformat()
                ),
                "path_node_sequences": [
                    list(item.path_nodes) for item in convergence.branches
                ],
                "scores": {
                    "demand_transmission": assessment.demand_transmission,
                    "bottleneck_strength": assessment.bottleneck_strength,
                    "economic_capture": assessment.economic_capture,
                    "reinvestment_runway": assessment.reinvestment_runway,
                    "triangulation": assessment.triangulation,
                    "expectation_gap": assessment.expectation_gap,
                },
                "evidence": [_evidence_reference(item) for item in assessment.evidence],
            }
        )
    return {
        "schema_version": REPLAY_RESULT_SCHEMA,
        "replay_id": result.replay_id,
        "as_of": result.as_of.isoformat(),
        "trigger_root_shock_id": result.trigger_root_shock_id,
        "freeze_sha256": freeze["freeze_sha256"],
        "status": "full",
        "promoted_node_count": len(result.assessments),
        "rankings": rankings,
    }


def write_replay_artifacts(
    output_dir: Path,
    *,
    freeze: dict[str, object],
    result: dict[str, object],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    freeze_path = output_dir / "replay_freeze.json"
    result_path = output_dir / "pre_news_rankings.json"
    for path, payload in ((freeze_path, freeze), (result_path, result)):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    return freeze_path, result_path
