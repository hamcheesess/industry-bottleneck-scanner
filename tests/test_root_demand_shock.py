import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.causal_expansion import CausalEvidence
from industry_bottleneck_scanner.root_demand_shock import (
    FileRootShockStore,
    RootDemandShock,
    approval_from_dict,
    approval_to_dict,
    evaluate_root_demand_shock,
)
from industry_bottleneck_scanner.root_shock_cli import main


DETECTED = datetime(2026, 8, 10, tzinfo=timezone.utc)
AS_OF = datetime(2026, 8, 11, tzinfo=timezone.utc)


def evidence(name: str, evidence_class: str, *, external: bool = True) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=name,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source-{name}",
        observed_at=DETECTED,
        summary=name,
        beneficiary_company_id="beneficiary",
        source_company_id="customer" if external else "beneficiary",
    )


def shock(*, as_of: datetime = AS_OF, strength: int = 5) -> RootDemandShock:
    return RootDemandShock(
        root_shock_id="ai-inference-deployment-2026q3",
        root_node="ai-inference-compute-deployment",
        label="AI inference compute deployment acceleration",
        mechanism="Hyperscalers increased deployed inference capacity and associated power demand.",
        market_trigger_id="industry-market-trigger-v1:electrical-equipment:2026-08-10",
        market_bucket="Electrical Equipment",
        detected_at=DETECTED,
        as_of=as_of,
        demand_strength=strength,
        evidence=(
            evidence("customer-plan", "customer_capacity_plan"),
            evidence("physical", "physical_industry_data"),
        ),
    )


def test_root_shock_requires_diverse_evidence_external_corroboration_and_strength() -> None:
    approved = evaluate_root_demand_shock(shock())
    weak = RootDemandShock(
        **{
            **shock().__dict__,
            "demand_strength": 2,
            "evidence": (
                evidence("self-a", "management_operating_commentary", external=False),
                evidence("self-b", "management_operating_commentary", external=False),
            ),
        }
    )
    rejected = evaluate_root_demand_shock(weak)

    assert approved.approved is True
    assert rejected.approved is False
    assert set(rejected.reasons) == {
        "insufficient_independent_evidence_classes",
        "no_external_corroboration",
        "weak_root_demand_strength",
    }


def test_root_shock_rejects_lookahead_evidence() -> None:
    future = evidence("future", "physical_industry_data")
    object.__setattr__(future, "observed_at", AS_OF + timedelta(seconds=1))
    with pytest.raises(ValueError, match="look-ahead"):
        RootDemandShock(**{**shock().__dict__, "evidence": (future,)})


def test_root_shock_store_is_append_only_and_latest_revision_controls_approval(tmp_path: Path) -> None:
    store = FileRootShockStore(tmp_path / "root-shocks.jsonl")
    first = evaluate_root_demand_shock(shock())
    store.append(first)
    assert approval_from_dict(approval_to_dict(first)) == first

    later_shock = shock(as_of=AS_OF + timedelta(days=1), strength=2)
    store.append(evaluate_root_demand_shock(later_shock))

    assert len(store.load()) == 2
    assert store.approved_shocks_as_of(as_of=AS_OF) == (first.shock,)
    assert store.approved_shocks_as_of(as_of=AS_OF + timedelta(days=1)) == ()
    with pytest.raises(ValueError, match="already exists"):
        store.append(first)


def test_root_shock_cli_records_approved_revision(tmp_path: Path) -> None:
    input_path = tmp_path / "root.json"
    registry_path = tmp_path / "roots.jsonl"
    payload = approval_to_dict(evaluate_root_demand_shock(shock()))["shock"]
    payload["schema_version"] = "root-demand-shock-input-v1"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--input", str(input_path), "--registry", str(registry_path)]) == 0
    assert FileRootShockStore(registry_path).approved_shocks_as_of(as_of=AS_OF) == (shock(),)
