from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.causal_expansion import CausalEvidence, ValueChainEdge
from industry_bottleneck_scanner.causal_graph import FileCausalGraphStore, evaluate_edge
from industry_bottleneck_scanner.causal_orchestration import run_causal_convergence
from industry_bottleneck_scanner.industry_state import (
    FileIndustryStateRegistry,
    IndustryStateSnapshot,
)
from industry_bottleneck_scanner.pre_news_replay import (
    HistoricalReplaySpec,
    PreNewsNodeJudgment,
    replay_spec_from_dict,
    run_pre_news_replay,
)
from industry_bottleneck_scanner.pre_news_replay_cli import main
from industry_bottleneck_scanner.root_demand_shock import (
    FileRootShockStore,
    RootDemandShock,
    evaluate_root_demand_shock,
)


PRE = datetime(2024, 10, 1, tzinfo=timezone.utc)
TRIGGER = datetime(2024, 11, 15, tzinfo=timezone.utc)
AS_OF = datetime(2024, 11, 20, tzinfo=timezone.utc)
TARGET = "large-power-transformers"
TRIGGER_ID = "industry-market-trigger-v1:electrical-equipment:2024-11-15"


def evidence(name: str, evidence_class: str, observed_at: datetime = PRE) -> CausalEvidence:
    return CausalEvidence(
        evidence_id=name,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=f"source-{name}",
        observed_at=observed_at,
        summary=name,
    )


def root(root_id: str, root_node: str, detected_at: datetime) -> RootDemandShock:
    return RootDemandShock(
        root_shock_id=root_id,
        root_node=root_node,
        label=f"Concrete demand expansion for {root_node}",
        mechanism=f"New capacity at {root_node} raises equipment demand.",
        market_trigger_id=(TRIGGER_ID if root_id == "ai-buildout" else f"trigger:{root_id}"),
        market_bucket="Electrical Equipment",
        detected_at=detected_at,
        as_of=AS_OF,
        demand_strength=5,
        evidence=(
            evidence(f"{root_id}-plan", "customer_capacity_plan", detected_at),
            evidence(f"{root_id}-physical", "physical_industry_data", detected_at),
        ),
    )


def edge(upstream: str, downstream: str, name: str) -> ValueChainEdge:
    return ValueChainEdge(
        upstream_node=upstream,
        downstream_node=downstream,
        relation="requires_capacity",
        mechanism=f"{upstream} requires {downstream}",
        demand_sensitivity=5,
        evidence=(
            evidence(f"{name}-dependency", "customer_architecture_dependency"),
            evidence(f"{name}-supplier", "supplier_capacity_expansion"),
        ),
    )


def stores(tmp_path: Path):
    roots = FileRootShockStore(tmp_path / "roots.jsonl")
    for item in (
        root("grid-upgrade", "grid-modernization", PRE),
        root("cloud-buildout", "cloud-capacity", PRE),
        root("ai-buildout", "ai-compute", TRIGGER),
    ):
        roots.append(evaluate_root_demand_shock(item))

    graph = FileCausalGraphStore(tmp_path / "graph.jsonl")
    for index, item in enumerate(
        (
            edge("grid-modernization", TARGET, "grid"),
            edge("cloud-capacity", TARGET, "cloud"),
            edge("ai-compute", "data-center-power", "ai-power"),
            edge("data-center-power", TARGET, "transformer"),
        )
    ):
        graph.append(evaluate_edge(f"edge-{index}", item, as_of=AS_OF))

    states = FileIndustryStateRegistry(tmp_path / "states.jsonl")
    states.append(
        IndustryStateSnapshot(
            node_id=TARGET,
            as_of=PRE,
            supply_inelasticity=5,
            lead_time_pressure=5,
            capacity_tightness=5,
            capacity_expansion_difficulty=5,
            qualification_barrier=4,
            pricing_pressure=4,
            evidence=(
                evidence("state-lead", "lead_time_constraint"),
                evidence("state-capacity", "capacity_utilization"),
            ),
        )
    )
    return roots, graph, states


def judgment() -> PreNewsNodeJudgment:
    return PreNewsNodeJudgment(
        node_id=TARGET,
        bottleneck_strength=5,
        economic_capture=4,
        reinvestment_runway=4,
        triangulation=5,
        expectation_gap=4,
        evidence=(evidence("competitor", "competitor_corroboration"),),
    )


def spec(*, held_out: tuple[str, ...] = ()) -> HistoricalReplaySpec:
    return HistoricalReplaySpec(
        replay_id="early-ai-electrical-v1",
        market_trigger_id=TRIGGER_ID,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
        held_out_evidence_ids=held_out,
        node_judgments=(judgment(),),
    )


def test_replay_feeds_promoted_convergence_into_existing_pre_news_ranker(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=states,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
    )

    replay = run_pre_news_replay(run, spec(held_out=("later-contract",)))

    assert [item.node_id for item in replay.assessments] == [TARGET]
    assert replay.assessments[0].demand_transmission == 5
    assert replay.ranked_nodes[0].stage == "pre_news_candidate"
    assert replay.ranked_nodes[0].score >= 70


def test_replay_fails_closed_on_missing_or_non_promoted_node_judgments(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=states,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
    )
    missing = HistoricalReplaySpec(
        replay_id="missing",
        market_trigger_id=TRIGGER_ID,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
        held_out_evidence_ids=(),
        node_judgments=(),
    )
    with pytest.raises(ValueError, match="missing judgments"):
        run_pre_news_replay(run, missing)

    extra = PreNewsNodeJudgment(
        node_id="unapproved-story-node",
        bottleneck_strength=5,
        economic_capture=5,
        reinvestment_runway=5,
        triangulation=5,
        expectation_gap=5,
    )
    unexpected = HistoricalReplaySpec(
        replay_id="unexpected",
        market_trigger_id=TRIGGER_ID,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
        held_out_evidence_ids=(),
        node_judgments=(judgment(), extra),
    )
    with pytest.raises(ValueError, match="non-promoted"):
        run_pre_news_replay(run, unexpected)


def test_replay_rejects_held_out_confirmation_leakage(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=states,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
    )

    with pytest.raises(ValueError, match="held-out evidence leaked"):
        run_pre_news_replay(run, spec(held_out=("state-lead",)))


def test_replay_does_not_report_full_when_nothing_was_promoted(tmp_path: Path) -> None:
    roots, graph, _ = stores(tmp_path)
    run = run_causal_convergence(
        root_store=roots,
        graph_store=graph,
        state_registry=FileIndustryStateRegistry(tmp_path / "empty-states.jsonl"),
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
    )
    empty = HistoricalReplaySpec(
        replay_id="nothing-promoted",
        market_trigger_id=TRIGGER_ID,
        trigger_root_shock_id="ai-buildout",
        as_of=AS_OF,
        held_out_evidence_ids=(),
        node_judgments=(),
    )

    with pytest.raises(ValueError, match="no promoted"):
        run_pre_news_replay(run, empty)


def test_cli_writes_fingerprinted_freeze_and_rankings(tmp_path: Path) -> None:
    roots, graph, states = stores(tmp_path)
    input_path = tmp_path / "replay-input.json"
    market_path = tmp_path / "market-trigger.json"
    output_dir = tmp_path / "output"
    input_path.write_text(
        json.dumps(
            {
                "schema_version": "historical-pre-news-replay-input-v1",
                "replay_id": "early-ai-electrical-v1",
                "market_trigger_id": TRIGGER_ID,
                "trigger_root_shock_id": "ai-buildout",
                "as_of": AS_OF.isoformat(),
                "held_out_evidence_ids": ["later-contract"],
                "node_judgments": [
                    {
                        "node_id": TARGET,
                        "bottleneck_strength": 5,
                        "economic_capture": 4,
                        "reinvestment_runway": 4,
                        "triangulation": 5,
                        "expectation_gap": 4,
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    market_path.write_text(
        json.dumps(
            {
                "schema_version": "industry-market-trigger-v1",
                "as_of": TRIGGER.date().isoformat(),
                "triggers": [
                    {"bucket": "Electrical Equipment", "triggered": True}
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "--input",
            str(input_path),
            "--market-trigger-artifact",
            str(market_path),
            "--root-shock-registry",
            str(roots.path),
            "--causal-graph-registry",
            str(graph.path),
            "--industry-state-registry",
            str(states.path),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0

    freeze = json.loads((output_dir / "replay_freeze.json").read_text())
    rankings = json.loads((output_dir / "pre_news_rankings.json").read_text())
    assert freeze["schema_version"] == "historical-pre-news-replay-freeze-v1"
    assert set(freeze["input_sha256"]) == {
        "replay_input",
        "market_trigger_artifact",
        "root_shock_registry",
        "causal_graph_registry",
        "industry_state_registry",
    }
    assert all(len(item) == 64 for item in freeze["input_sha256"].values())
    assert rankings["status"] == "full"
    assert rankings["freeze_sha256"] == freeze["freeze_sha256"]
    assert rankings["rankings"][0]["node_id"] == TARGET
    assert ["ai-compute", "data-center-power", TARGET] in rankings["rankings"][0][
        "path_node_sequences"
    ]


def test_committed_transformer_replay_input_stays_conservative() -> None:
    payload = json.loads(
        Path("experiments/pre_news_replay/early-ai-electrical-2026-08-21.json").read_text()
    )

    frozen = replay_spec_from_dict(payload)

    assert frozen.replay_id == "early-ai-electrical-2026-08-21-v1"
    assert frozen.as_of == datetime(2026, 8, 21, 23, 59, 59, tzinfo=timezone.utc)
    assert frozen.held_out_evidence_ids == ()
    assert len(frozen.node_judgments) == 1
    judgment = frozen.node_judgments[0]
    assert judgment.node_id == TARGET
    assert (
        judgment.bottleneck_strength,
        judgment.economic_capture,
        judgment.reinvestment_runway,
        judgment.triangulation,
        judgment.expectation_gap,
    ) == (5, 2, 4, 5, 1)
    assert judgment.economic_capture < 3
