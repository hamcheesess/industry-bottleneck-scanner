from __future__ import annotations

import json
from pathlib import Path

import pytest

from industry_bottleneck_scanner.industry_analysis_report import (
    REQUIRED_SECTIONS,
    build_industry_analysis_report,
    render_industry_analysis_markdown,
)
from industry_bottleneck_scanner.industry_analysis_report_cli import main


INPUT_PATH = Path(
    "experiments/industry_analysis/large-power-transformers-2026-08-21.ko.json"
)


def analysis_input() -> dict[str, object]:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def referenced_evidence_ids(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_ids" and isinstance(item, list):
                found.update(str(evidence_id) for evidence_id in item)
            else:
                found.update(referenced_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(referenced_evidence_ids(item))
    return found


def replay_artifacts(
    payload: dict[str, object], *, future_evidence_id: str | None = None
) -> tuple[dict[str, object], dict[str, object]]:
    evidence_classes = (
        "physical_industry_data",
        "regulatory_or_permitting",
        "supplier_capacity_expansion",
        "lead_time_constraint",
    )
    evidence = []
    for index, evidence_id in enumerate(sorted(referenced_evidence_ids(payload))):
        observed_at = (
            "2026-08-22T00:00:00+00:00"
            if evidence_id == future_evidence_id
            else "2025-01-01T00:00:00+00:00"
        )
        evidence.append(
            {
                "evidence_id": evidence_id,
                "evidence_class": evidence_classes[index % len(evidence_classes)],
                "source_id": f"source:{evidence_id}",
                "observed_at": observed_at,
            }
        )
    freeze = {
        "schema_version": "historical-pre-news-replay-freeze-v1",
        "replay_id": payload["replay_id"],
        "as_of": payload["as_of"],
        "freeze_sha256": "f" * 64,
    }
    result = {
        "schema_version": "historical-pre-news-replay-result-v1",
        "replay_id": payload["replay_id"],
        "as_of": payload["as_of"],
        "freeze_sha256": freeze["freeze_sha256"],
        "status": "full",
        "rankings": [
            {
                "node_id": payload["node_id"],
                "stage": "evidence_backed",
                "score": 73.0,
                "convergence_stage": "pre_shock_bottleneck",
                "gate_reasons": [],
                "independent_root_shock_ids": [
                    "ai-data-center-electric-load-expansion-2026q3"
                ],
                "path_node_sequences": [
                    [
                        "ai-data-center-electric-load-growth",
                        "large-load-grid-interconnection-capacity",
                        "large-power-transformers",
                    ]
                ],
                "scores": {
                    "demand_transmission": 4,
                    "bottleneck_strength": 5,
                    "economic_capture": 2,
                    "reinvestment_runway": 4,
                    "triangulation": 5,
                    "expectation_gap": 1,
                },
                "evidence": evidence,
            }
        ],
    }
    return result, freeze


def test_committed_korean_industry_analysis_is_deep_and_evidence_bound() -> None:
    payload = analysis_input()
    result, freeze = replay_artifacts(payload)

    report = build_industry_analysis_report(
        payload,
        result,
        freeze,
        analysis_input_sha256="a" * 64,
    )
    markdown = render_industry_analysis_markdown(report)

    assert report["schema_version"] == "industry-analysis-report-v1"
    assert report["strict_as_of"] is True
    assert report["narrative_required"] is True
    assert report["security_level_conclusion"] is False
    assert report["evidence_reference_count"] == 14
    assert report["evidence_class_count"] == 4
    assert set(report["sections"]) == set(REQUIRED_SECTIONS)
    assert "## 한눈에 보는 결론" in markdown
    assert "## 공급이 빨리 늘지 못하는 이유" in markdown
    assert "## 시장 기대에 반영된 것과 아직 모르는 것" in markdown
    assert "## 점수를 사람의 언어로 해석하기" in markdown
    assert "73점은 성공확률이나 기대수익률" in markdown


def test_report_rejects_claim_evidence_outside_replay() -> None:
    payload = analysis_input()
    result, freeze = replay_artifacts(payload)
    executive = payload["executive_call"]
    assert isinstance(executive, dict)
    evidence_ids = executive["evidence_ids"]
    assert isinstance(evidence_ids, list)
    evidence_ids.append("later-outcome-contract")

    with pytest.raises(ValueError, match="outside replay"):
        build_industry_analysis_report(
            payload,
            result,
            freeze,
            analysis_input_sha256="a" * 64,
        )


def test_report_rejects_post_cutoff_replay_evidence() -> None:
    payload = analysis_input()
    evidence_id = sorted(referenced_evidence_ids(payload))[0]
    result, freeze = replay_artifacts(payload, future_evidence_id=evidence_id)

    with pytest.raises(ValueError, match="post-cutoff"):
        build_industry_analysis_report(
            payload,
            result,
            freeze,
            analysis_input_sha256="a" * 64,
        )


def test_report_rejects_missing_industry_section_and_freeze_mismatch() -> None:
    payload = analysis_input()
    result, freeze = replay_artifacts(payload)
    sections = payload["sections"]
    assert isinstance(sections, dict)
    sections.pop("economic_capture")
    with pytest.raises(ValueError, match="required industry analysis sections"):
        build_industry_analysis_report(
            payload,
            result,
            freeze,
            analysis_input_sha256="a" * 64,
        )

    payload = analysis_input()
    result, freeze = replay_artifacts(payload)
    result["freeze_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprints do not match"):
        build_industry_analysis_report(
            payload,
            result,
            freeze,
            analysis_input_sha256="a" * 64,
        )


def test_cli_writes_reader_first_json_and_markdown(tmp_path: Path) -> None:
    payload = analysis_input()
    result, freeze = replay_artifacts(payload)
    input_path = tmp_path / "analysis.json"
    result_path = tmp_path / "rankings.json"
    freeze_path = tmp_path / "freeze.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    result_path.write_text(json.dumps(result), encoding="utf-8")
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    output_dir = tmp_path / "output"

    assert main(
        [
            "--analysis-input",
            str(input_path),
            "--replay-result",
            str(result_path),
            "--replay-freeze",
            str(freeze_path),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    report = json.loads((output_dir / "industry_analysis.json").read_text())
    markdown = (output_dir / "industry_analysis.ko.md").read_text()
    assert report["analysis_input_sha256"] != ""
    assert report["report_sha256"] != ""
    assert "# 대형 전력변압기 산업" in markdown


def test_score_explanations_are_not_allowed_to_replace_narrative() -> None:
    payload = analysis_input()
    result, freeze = replay_artifacts(payload)
    sections = payload["sections"]
    assert isinstance(sections, dict)
    sections["industry_structure"] = []

    with pytest.raises(ValueError, match="must contain at least one claim"):
        build_industry_analysis_report(
            payload,
            result,
            freeze,
            analysis_input_sha256="a" * 64,
        )


def test_production_replay_requires_reader_facing_analysis() -> None:
    workflow = Path(".github/workflows/pre-news-replay-production.yml").read_text()

    assert "analysis_input_path:" in workflow
    assert "ibs-industry-analysis-report" in workflow
    assert "industry_analysis.json" in workflow
    assert "industry_analysis.ko.md" in workflow
    assert '"narrative_required": True' in workflow
    assert "## 공급이 빨리 늘지 못하는 이유" in workflow
    assert "## 산업의 경제성과 수익 포착 조건" in workflow
