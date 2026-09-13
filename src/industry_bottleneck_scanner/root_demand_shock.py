from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .causal_expansion import CausalEvidence

ROOT_SHOCK_SCHEMA_VERSION = "root-demand-shock-v1"


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class RootDemandShock:
    root_shock_id: str
    root_node: str
    label: str
    mechanism: str
    market_trigger_id: str
    market_bucket: str
    detected_at: datetime
    as_of: datetime
    demand_strength: int
    evidence: tuple[CausalEvidence, ...]

    def __post_init__(self) -> None:
        for name in (
            "root_shock_id",
            "root_node",
            "label",
            "mechanism",
            "market_trigger_id",
            "market_bucket",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        _require_aware("detected_at", self.detected_at)
        _require_aware("as_of", self.as_of)
        if self.as_of < self.detected_at:
            raise ValueError("root shock as_of cannot precede detected_at")
        if isinstance(self.demand_strength, bool) or not isinstance(self.demand_strength, int):
            raise ValueError("demand_strength must be an integer from 0 to 5")
        if not 0 <= self.demand_strength <= 5:
            raise ValueError("demand_strength must be an integer from 0 to 5")
        for item in self.evidence:
            _require_aware(f"evidence {item.evidence_id} observed_at", item.observed_at)
        future = [item.evidence_id for item in self.evidence if item.observed_at > self.as_of]
        if future:
            raise ValueError("look-ahead root-shock evidence is not allowed: " + ",".join(sorted(future)))


@dataclass(frozen=True)
class RootShockApproval:
    shock: RootDemandShock
    approved: bool
    reasons: tuple[str, ...]
    evidence_classes: tuple[str, ...]


def evaluate_root_demand_shock(
    shock: RootDemandShock,
    *,
    min_independent_evidence_classes: int = 2,
    external_corroboration_required: bool = True,
) -> RootShockApproval:
    if min_independent_evidence_classes < 1:
        raise ValueError("min_independent_evidence_classes must be at least 1")
    classes = tuple(sorted({item.evidence_class for item in shock.evidence}))
    reasons: list[str] = []
    if len(classes) < min_independent_evidence_classes:
        reasons.append("insufficient_independent_evidence_classes")
    if external_corroboration_required and not any(
        item.externally_corroborating for item in shock.evidence
    ):
        reasons.append("no_external_corroboration")
    if shock.demand_strength < 3:
        reasons.append("weak_root_demand_strength")
    return RootShockApproval(
        shock=shock,
        approved=not reasons,
        reasons=tuple(reasons),
        evidence_classes=classes,
    )


def _evidence_to_dict(item: CausalEvidence) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "evidence_class": item.evidence_class,
        "source_id": item.source_id,
        "observed_at": item.observed_at.isoformat(),
        "summary": item.summary,
        "beneficiary_company_id": item.beneficiary_company_id,
        "source_company_id": item.source_company_id,
    }


def _evidence_from_dict(payload: dict[str, object]) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=str(payload["evidence_id"]),
        evidence_class=str(payload["evidence_class"]),  # type: ignore[arg-type]
        source_id=str(payload["source_id"]),
        observed_at=datetime.fromisoformat(str(payload["observed_at"])),
        summary=str(payload["summary"]),
        beneficiary_company_id=(
            None
            if payload.get("beneficiary_company_id") is None
            else str(payload["beneficiary_company_id"])
        ),
        source_company_id=(
            None if payload.get("source_company_id") is None else str(payload["source_company_id"])
        ),
    )


def approval_to_dict(approval: RootShockApproval) -> dict[str, object]:
    shock = approval.shock
    return {
        "schema_version": ROOT_SHOCK_SCHEMA_VERSION,
        "approved": approval.approved,
        "reasons": list(approval.reasons),
        "evidence_classes": list(approval.evidence_classes),
        "shock": {
            "root_shock_id": shock.root_shock_id,
            "root_node": shock.root_node,
            "label": shock.label,
            "mechanism": shock.mechanism,
            "market_trigger_id": shock.market_trigger_id,
            "market_bucket": shock.market_bucket,
            "detected_at": shock.detected_at.isoformat(),
            "as_of": shock.as_of.isoformat(),
            "demand_strength": shock.demand_strength,
            "evidence": [_evidence_to_dict(item) for item in shock.evidence],
        },
    }


def approval_from_dict(payload: dict[str, object]) -> RootShockApproval:
    if payload.get("schema_version") != ROOT_SHOCK_SCHEMA_VERSION:
        raise ValueError(f"unsupported root-shock schema: {payload.get('schema_version')!r}")
    raw = payload.get("shock")
    if not isinstance(raw, dict):
        raise ValueError("root-shock payload requires shock object")
    shock = root_shock_from_dict(raw)
    return RootShockApproval(
        shock=shock,
        approved=bool(payload["approved"]),
        reasons=tuple(str(item) for item in payload.get("reasons", [])),  # type: ignore[arg-type]
        evidence_classes=tuple(
            str(item) for item in payload.get("evidence_classes", [])  # type: ignore[arg-type]
        ),
    )


def root_shock_from_dict(raw: dict[str, object]) -> RootDemandShock:
    raw_evidence = raw.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("root-shock evidence must be a list")
    return RootDemandShock(
        root_shock_id=str(raw["root_shock_id"]),
        root_node=str(raw["root_node"]),
        label=str(raw["label"]),
        mechanism=str(raw["mechanism"]),
        market_trigger_id=str(raw["market_trigger_id"]),
        market_bucket=str(raw["market_bucket"]),
        detected_at=datetime.fromisoformat(str(raw["detected_at"])),
        as_of=datetime.fromisoformat(str(raw["as_of"])),
        demand_strength=int(raw["demand_strength"]),
        evidence=tuple(
            _evidence_from_dict(item) for item in raw_evidence if isinstance(item, dict)
        ),
    )


class FileRootShockStore:
    """Append-only root-shock approval/revision history."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, approval: RootShockApproval) -> None:
        shock = approval.shock
        if any(
            item.shock.root_shock_id == shock.root_shock_id and item.shock.as_of == shock.as_of
            for item in self.load()
        ):
            raise ValueError("root-shock revision already exists for root_shock_id and as_of")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(approval_to_dict(approval), sort_keys=True) + "\n")

    def load(self) -> tuple[RootShockApproval, ...]:
        if not self.path.exists():
            return ()
        approvals: list[RootShockApproval] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{self.path}:{line_number}: invalid JSON") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{self.path}:{line_number}: root-shock row must be an object")
            approvals.append(approval_from_dict(payload))
        approvals.sort(key=lambda item: (item.shock.root_shock_id, item.shock.as_of))
        return tuple(approvals)

    def latest_as_of(self, *, as_of: datetime) -> tuple[RootShockApproval, ...]:
        _require_aware("as_of", as_of)
        latest: dict[str, RootShockApproval] = {}
        for item in self.load():
            if item.shock.as_of <= as_of:
                previous = latest.get(item.shock.root_shock_id)
                if previous is None or item.shock.as_of > previous.shock.as_of:
                    latest[item.shock.root_shock_id] = item
        return tuple(latest[key] for key in sorted(latest))

    def approved_shocks_as_of(self, *, as_of: datetime) -> tuple[RootDemandShock, ...]:
        return tuple(item.shock for item in self.latest_as_of(as_of=as_of) if item.approved)


def approved_shock_by_id(
    approvals: Iterable[RootShockApproval],
    root_shock_id: str,
) -> RootDemandShock | None:
    matches = [item.shock for item in approvals if item.approved and item.shock.root_shock_id == root_shock_id]
    return max(matches, key=lambda item: item.as_of) if matches else None
