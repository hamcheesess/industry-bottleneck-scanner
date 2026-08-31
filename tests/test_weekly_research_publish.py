from __future__ import annotations

import json

import pytest

from industry_bottleneck_scanner.weekly_research_publish import (
    build_weekly_site_export,
    write_weekly_site_artifacts,
)
from industry_bottleneck_scanner.weekly_research_publish_cli import main


def payload() -> dict[str, object]:
    return {
        "schema_version": "weekly-industry-research-input-v1",
        "run_id": "weekly-2026-08-31",
        "as_of": "2026-08-31T12:00:00+00:00",
        "cadence": "weekly",
        "language": "ko",
        "candidates": [
            {
                "candidate_id": "sic-3440",
                "bucket": "SIC 3440 - 구조금속 제품",
                "status": "final_report_published",
                "stage": "final_report",
                "observed_at": "2026-08-31T10:00:00+00:00",
                "first_detected_as_of": "2025-08-29",
                "evidence_count": 17,
                "source_classes": [
                    "issuer_primary",
                    "government_regulator",
                    "industry_technical",
                    "physical_market_data",
                ],
                "report_id": "lpt-2026-08-31",
                "financial_scenario_id": "lpt-financial-2026-08-31",
            },
            {
                "candidate_id": "sparse-insurance",
                "bucket": "손해·건강보험",
                "status": "rejected",
                "stage": "operating_evidence",
                "observed_at": "2026-08-31T09:00:00+00:00",
                "first_detected_as_of": "2026-08-21",
                "evidence_count": 1,
                "source_classes": ["issuer_primary"],
                "reason_code": "sparse_independent_operating_evidence",
                "reason_summary_ko": "직접 운영 근거가 한 개 기업에만 있어 산업 전반의 병목으로 일반화할 수 없습니다.",
            },
        ],
        "financial_scenarios": [
            {
                "scenario_run_id": "lpt-financial-2026-08-31",
                "candidate_id": "sic-3440",
                "node_id": "large-power-transformers",
                "as_of": "2026-08-31T10:30:00+00:00",
                "readiness_status": "senior_review_ready",
                "decision_status": "advance_to_deeper_work",
                "gate_reasons": [],
                "base_12m_return": 0.30,
                "downside_12m_return": -0.10,
                "upside_12m_return": 0.55,
                "reward_to_downside": 3.0,
                "base_12m_operating_income_gap": 90.0,
                "base_12m_fcf_gap": 75.0,
                "scenario_object_key": "scenarios/lpt-financial-2026-08-31.json",
                "scenario_sha256": "b" * 64,
                "investor_summary_ko": {
                    "bottleneck_to_revenue": "산업 병목 물량에서 기업이 확보 가능한 물량과 증분 매출로 이어지는 경로를 설명합니다.",
                    "earnings_and_cash_flow": "증분 매출이 영업이익과 잉여현금흐름으로 전환되는 과정을 보수적으로 설명합니다.",
                    "market_expectations_gap": "자체 추정 영업이익과 현금흐름을 시장 기대치와 비교해 차이를 설명합니다.",
                    "risk_reward": "하방·기준·상방 시나리오의 기대수익률과 보상 대비 하방 위험을 설명합니다.",
                    "research_decision": "정량 관문을 모두 통과해 추가 기업 조사를 진행할 수 있는 상태입니다.",
                },
            }
        ],
        "final_reports": [
            {
                "report_id": "lpt-2026-08-31",
                "candidate_id": "sic-3440",
                "title_ko": "대형 전력변압기 병목과 투자 전환 가능성",
                "report_object_key": "reports/2026/08/lpt-2026-08-31.json",
                "report_sha256": "a" * 64,
                "published_at": "2026-08-31T11:00:00+00:00",
                "source_classes": [
                    "issuer_primary",
                    "government_regulator",
                    "industry_technical",
                    "physical_market_data",
                ],
                "independent_source_count": 5,
                "token_usage": {
                    "input_tokens": 24000,
                    "output_tokens": 7200,
                    "cached_input_tokens": 6000,
                },
                "quality_feedback": {
                    "useful_claim_count": 24,
                    "unsupported_claim_count": 0,
                    "unique_source_count": 12,
                    "duplicate_evidence_ratio": 0.08,
                },
            }
        ],
    }


def test_site_export_keeps_compact_rejection_and_final_reports_only() -> None:
    site, feedback = build_weekly_site_export(payload())

    assert site["publication_policy"] == {
        "final_reports_only": True,
        "draft_content_stored": False,
        "compact_rejection_statuses": True,
        "gpt_v1_quality_priority": True,
    }
    assert site["summary"] == {
        "candidate_count": 2,
        "active_research_count": 0,
        "rejected_count": 1,
        "final_report_count": 1,
        "financial_scenario_count": 1,
    }
    assert site["research_policy"]["quality_before_token_efficiency"] is True
    assert site["research_policy"]["report_generation"] == "finalists_only"
    assert "diverse_source_discovery" in site["research_policy"]["gpt_required_work"]
    rejected = next(row for row in site["candidate_statuses"] if row["status"] == "rejected")
    assert rejected["stage"] == "operating_evidence"
    assert "한 개 기업" in rejected["reason_summary_ko"]
    assert set(site["final_reports"][0]) == {
        "report_id",
        "candidate_id",
        "title_ko",
        "report_object_key",
        "report_sha256",
        "published_at",
        "source_classes",
        "independent_source_count",
        "token_usage",
    }
    assert site["financial_scenarios"][0]["decision_status"] == "advance_to_deeper_work"
    assert "증분 매출" in site["financial_scenarios"][0]["investor_summary_ko"][
        "bottleneck_to_revenue"
    ]
    assert feedback["report_count"] == 1
    assert feedback["reports"][0]["efficiency"]["output_tokens_per_useful_claim"] == 300.0


def test_draft_and_prompt_content_are_rejected_before_site_export() -> None:
    value = payload()
    value["candidates"][1]["research_notes"] = "long hidden draft"

    with pytest.raises(ValueError, match="must not contain draft or prompt content"):
        build_weekly_site_export(value)


def test_rejected_industry_requires_short_korean_reader_reason() -> None:
    value = payload()
    value["candidates"][1]["reason_summary_ko"] = "근거 부족"

    with pytest.raises(ValueError, match="10-180 character Korean summary"):
        build_weekly_site_export(value)


def test_final_report_requires_diverse_independent_sources() -> None:
    value = payload()
    value["final_reports"][0]["source_classes"] = [
        "issuer_primary",
        "government_regulator",
        "industry_technical",
    ]

    with pytest.raises(ValueError, match="at least four source classes"):
        build_weekly_site_export(value)


def test_unsupported_claim_blocks_final_report_publication() -> None:
    value = payload()
    value["final_reports"][0]["quality_feedback"]["unsupported_claim_count"] = 1

    with pytest.raises(ValueError, match="cannot publish unsupported claims"):
        build_weekly_site_export(value)


def test_efficiency_feedback_flags_avoidable_token_cost_without_blocking_quality() -> None:
    value = payload()
    report = value["final_reports"][0]
    report["token_usage"] = {
        "input_tokens": 50000,
        "output_tokens": 18000,
        "cached_input_tokens": 1000,
    }
    report["quality_feedback"]["useful_claim_count"] = 20
    report["quality_feedback"]["unique_source_count"] = 8
    report["quality_feedback"]["duplicate_evidence_ratio"] = 0.3

    _, feedback = build_weekly_site_export(value)
    recommendations = feedback["reports"][0]["recommendations_ko"]
    assert len(recommendations) == 4
    assert any("원문 길이" in item for item in recommendations)
    assert any("핵심 주장 밀도" in item for item in recommendations)
    assert any("반복 인용" in item for item in recommendations)
    assert any("재사용률" in item for item in recommendations)


def test_cli_writes_site_and_feedback_artifacts(tmp_path, monkeypatch, capsys) -> None:
    input_path = tmp_path / "weekly.json"
    input_path.write_text(json.dumps(payload(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ibs-weekly-research-publish",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    main()

    site = json.loads((output_dir / "weekly_research_status.json").read_text())
    feedback = json.loads((output_dir / "token_efficiency_feedback.json").read_text())
    assert site["schema_version"] == "weekly-industry-research-site-export-v1"
    assert feedback["schema_version"] == "report-token-efficiency-feedback-v1"
    assert "final_reports=1" in capsys.readouterr().out


def test_writer_never_materializes_report_drafts(tmp_path) -> None:
    site, feedback = build_weekly_site_export(payload())
    site_path, feedback_path = write_weekly_site_artifacts(tmp_path, site, feedback)

    assert site_path.name == "weekly_research_status.json"
    assert feedback_path.name == "token_efficiency_feedback.json"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "token_efficiency_feedback.json",
        "weekly_research_status.json",
    ]


def test_final_report_requires_advanced_financial_scenario() -> None:
    value = payload()
    value["financial_scenarios"][0]["decision_status"] = "valuation_gated"
    value["financial_scenarios"][0]["gate_reasons"] = ["base_return_below_hurdle"]

    with pytest.raises(ValueError, match="requires an advanced financial scenario"):
        build_weekly_site_export(value)


def test_financial_scenario_must_link_to_same_candidate() -> None:
    value = payload()
    value["financial_scenarios"][0]["candidate_id"] = "different-candidate"

    with pytest.raises(ValueError, match="has no weekly candidate"):
        build_weekly_site_export(value)
