from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from .causal_expansion import CausalEvidence

IndustryConstraintStage = Literal[
    "unknown",
    "normal",
    "tightening",
    "constrained",
    "severely_constrained",
]

STATE_SCHEMA_VERSION = "industry-state-v1"

STATE_WEIGHTS: dict[str, float] = {
    "supply_inelasticity": 0.25,
    "lead_time_pressure": 0.20,
    "capacity_tightness": 0.20,
    "capacity_expansion_difficulty": 0.15,
    "qualification_barrier": 0.10,
    "pricing_pressure": 0.10,
}


def _validate_score(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class IndustryStateSnapshot:
    """Evidence-backed state of a value-chain node before a new market shock arrives.

    Scores are directional: 5 always means a stronger constraint / tighter state.
    The snapshot is intentionally independent of any later demand shock so it can be
    queried as a pre-shock condition during historical replay.
    """

    node_id: str
    as_of: datetime
    supply_inelasticity: int
    lead_time_pressure: int
    capacity_tightness: int
    capacity_expansion_difficulty: int
    qualification_barrier: int
    pricing_pressure: int
    evidence: tuple[CausalEvidence, ...] = ()

    def __post_init__(self) -> None:
        _require_aware("as_of", self.as_of)
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        for name in STATE_WEIGHTS:
            _validate_score(name, getattr(self, name))
        future = [item.evidence_id for item in self.evidence if item.observed_at > self.as_of]
        if future:
            raise ValueError(
                "look-ahead evidence after industry-state as_of is not allowed: "
                + ",".join(sorted(future))
            )

    @property
    def independent_evidence_classes(self) -> tuple[str, ...]:
        return tuple(sorted({item.evidence_class for item in self.evidence}))

    @property
    def constraint_score(self) -> float:
        weighted = sum(getattr(self, name) * weight for name, weight in STATE_WEIGHTS.items())
        return round(weighted / 5.0 * 100.0, 2)

    @property
    def stage(self) -> IndustryConstraintStage:
        if len(self.independent_evidence_classes) < 2:
            return "unknown"
        score = self.constraint_score
        if score >= 80:
            return "severely_constrained"
        if score >= 65:
            return "constrained"
        if score >= 45:
            return "tightening"
        return "normal"


def snapshot_to_dict(snapshot: IndustryStateSnapshot) -> dict[str, object]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "node_id": snapshot.node_id,
        "as_of": snapshot.as_of.isoformat(),
        "supply_inelasticity": snapshot.supply_inelasticity,
        "lead_time_pressure": snapshot.lead_time_pressure,
        "capacity_tightness": snapshot.capacity_tightness,
        "capacity_expansion_difficulty": snapshot.capacity_expansion_difficulty,
        "qualification_barrier": snapshot.qualification_barrier,
        "pricing_pressure": snapshot.pricing_pressure,
        "constraint_score": snapshot.constraint_score,
        "stage": snapshot.stage,
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "evidence_class": item.evidence_class,
                "source_id": item.source_id,
                "observed_at": item.observed_at.isoformat(),
                "summary": item.summary,
                "beneficiary_company_id": item.beneficiary_company_id,
                "source_company_id": item.source_company_id,
            }
            for item in snapshot.evidence
        ],
    }


def snapshot_from_dict(payload: dict[str, object]) -> IndustryStateSnapshot:
    schema = payload.get("schema_version")
    if schema != STATE_SCHEMA_VERSION:
        raise ValueError(f"unsupported industry-state schema: {schema!r}")
    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("industry-state evidence must be a list")
    evidence: list[CausalEvidence] = []
    for raw in raw_evidence:
        if not isinstance(raw, dict):
            raise ValueError("industry-state evidence rows must be objects")
        evidence.append(
            CausalEvidence(
                evidence_id=str(raw["evidence_id"]),
                evidence_class=str(raw["evidence_class"]),  # type: ignore[arg-type]
                source_id=str(raw["source_id"]),
                observed_at=datetime.fromisoformat(str(raw["observed_at"])),
                summary=str(raw["summary"]),
                beneficiary_company_id=(
                    None if raw.get("beneficiary_company_id") is None else str(raw["beneficiary_company_id"])
                ),
                source_company_id=(
                    None if raw.get("source_company_id") is None else str(raw["source_company_id"])
                ),
            )
        )
    return IndustryStateSnapshot(
        node_id=str(payload["node_id"]),
        as_of=datetime.fromisoformat(str(payload["as_of"])),
        supply_inelasticity=int(payload["supply_inelasticity"]),
        lead_time_pressure=int(payload["lead_time_pressure"]),
        capacity_tightness=int(payload["capacity_tightness"]),
        capacity_expansion_difficulty=int(payload["capacity_expansion_difficulty"]),
        qualification_barrier=int(payload["qualification_barrier"]),
        pricing_pressure=int(payload["pricing_pressure"]),
        evidence=tuple(evidence),
    )


class FileIndustryStateRegistry:
    """Append-only JSONL history of industry-state snapshots.

    Keeping historical snapshots rather than overwriting the latest state is critical for
    look-ahead-safe replay: a market trigger may only query a state that was observable
    strictly before the trigger timestamp.
    """

    def __init__(self, path: Path):
        self.path = path

    def append(self, snapshot: IndustryStateSnapshot) -> None:
        if any(
            item.node_id == snapshot.node_id and item.as_of == snapshot.as_of
            for item in self.load()
        ):
            raise ValueError("industry-state snapshot already exists for node_id and as_of")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot_to_dict(snapshot), sort_keys=True) + "\n")

    def load(self) -> tuple[IndustryStateSnapshot, ...]:
        if not self.path.exists():
            return ()
        snapshots: list[IndustryStateSnapshot] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{self.path}:{line_number}: invalid JSON") from exc
                if not isinstance(payload, dict):
                    raise ValueError(f"{self.path}:{line_number}: snapshot must be an object")
                snapshots.append(snapshot_from_dict(payload))
        snapshots.sort(key=lambda item: (item.node_id, item.as_of))
        return tuple(snapshots)

    def latest_before(
        self,
        *,
        node_id: str,
        cutoff: datetime,
        strict: bool = True,
    ) -> IndustryStateSnapshot | None:
        _require_aware("cutoff", cutoff)
        eligible = [
            item
            for item in self.load()
            if item.node_id == node_id and (item.as_of < cutoff if strict else item.as_of <= cutoff)
        ]
        if not eligible:
            return None
        return max(eligible, key=lambda item: item.as_of)
