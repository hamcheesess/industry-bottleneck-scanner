from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


ANALYSIS_INPUT_SCHEMA = "industry-analysis-narrative-input-v1"
ANALYSIS_REPORT_SCHEMA = "industry-analysis-report-v1"
REPLAY_FREEZE_SCHEMA = "historical-pre-news-replay-freeze-v1"
REPLAY_RESULT_SCHEMA = "historical-pre-news-replay-result-v1"

REQUIRED_SECTIONS = (
    "industry_structure",
    "demand_drivers",
    "value_chain_transmission",
    "bottleneck_mechanics",
    "supply_response",
    "economic_capture",
    "expectations_and_pricing",
    "risks_and_falsifiers",
    "monitoring_signals",
)
REQUIRED_SCORE_KEYS = (
    "demand_transmission",
    "bottleneck_strength",
    "economic_capture",
    "reinvestment_runway",
    "triangulation",
    "expectation_gap",
)
REQUIRED_SCENARIOS = {"base", "upside", "downside"}
ALLOWED_CLAIM_TYPES = {"fact", "inference", "uncertainty", "scenario"}

SECTION_TITLES_KO = {
    "industry_structure": "산업의 구조와 제품의 역할",
    "demand_drivers": "수요는 어디에서 오는가",
    "value_chain_transmission": "수요가 병목으로 전달되는 경로",
    "bottleneck_mechanics": "공급이 빨리 늘지 못하는 이유",
    "supply_response": "공급업체의 대응과 병목의 지속 가능성",
    "economic_capture": "산업의 경제성과 수익 포착 조건",
    "expectations_and_pricing": "시장 기대에 반영된 것과 아직 모르는 것",
    "risks_and_falsifiers": "반대 논리와 분석이 틀렸다고 판단할 조건",
    "monitoring_signals": "앞으로 확인해야 할 신호",
}
CLAIM_TYPE_LABELS_KO = {
    "fact": "확인된 사실",
    "inference": "근거 기반 해석",
    "uncertainty": "미확인 사항",
    "scenario": "조건부 시나리오",
}
SCORE_TITLES_KO = {
    "demand_transmission": "수요 전달력",
    "bottleneck_strength": "병목 강도",
    "economic_capture": "경제적 수익 포착",
    "reinvestment_runway": "재투자·증설 기간",
    "triangulation": "독립 근거의 교차 확인",
    "expectation_gap": "시장 기대와의 차이",
}


def _required_text(payload: dict[str, object], key: str, *, minimum: int = 1) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{key} must be text with at least {minimum} characters")
    return value.strip()


def _aware_datetime(value: object, name: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def _string_list(value: object, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    result = [item.strip() for item in value]
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def _parse_claim(
    raw: object,
    *,
    name: str,
    allowed_evidence_ids: set[str],
) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    label = _required_text(raw, "label")
    text = _required_text(raw, "text", minimum=40)
    claim_type = _required_text(raw, "claim_type")
    if claim_type not in ALLOWED_CLAIM_TYPES:
        raise ValueError(f"{name} has unsupported claim_type: {claim_type}")
    evidence_ids = _string_list(raw.get("evidence_ids"), f"{name}.evidence_ids")
    unknown = sorted(set(evidence_ids) - allowed_evidence_ids)
    if unknown:
        raise ValueError(f"{name} references evidence outside replay: {','.join(unknown)}")
    if claim_type in {"fact", "inference"} and not evidence_ids:
        raise ValueError(f"{name} {claim_type} claims require replay evidence")
    return {
        "label": label,
        "text": text,
        "claim_type": claim_type,
        "evidence_ids": evidence_ids,
    }


def _evidence_index(ranking: dict[str, object], as_of: datetime) -> dict[str, dict[str, object]]:
    raw_evidence = ranking.get("evidence")
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise ValueError("ranking evidence must be a non-empty list")
    by_id: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(raw_evidence):
        if not isinstance(raw, dict):
            raise ValueError(f"ranking evidence row {index} must be an object")
        evidence_id = _required_text(raw, "evidence_id")
        evidence_class = _required_text(raw, "evidence_class")
        source_id = _required_text(raw, "source_id")
        observed_at = _aware_datetime(raw.get("observed_at"), "evidence observed_at")
        if observed_at > as_of:
            raise ValueError(f"post-cutoff evidence in replay ranking: {evidence_id}")
        normalized = {
            "evidence_id": evidence_id,
            "evidence_class": evidence_class,
            "source_id": source_id,
            "observed_at": observed_at.isoformat(),
        }
        existing = by_id.get(evidence_id)
        if existing is not None and existing != normalized:
            raise ValueError(f"conflicting replay evidence ID: {evidence_id}")
        by_id[evidence_id] = normalized
    return by_id


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_industry_analysis_report(
    analysis_input: dict[str, object],
    replay_result: dict[str, object],
    replay_freeze: dict[str, object],
    *,
    analysis_input_sha256: str,
) -> dict[str, object]:
    if analysis_input.get("schema_version") != ANALYSIS_INPUT_SCHEMA:
        raise ValueError("unsupported industry analysis input schema")
    if replay_result.get("schema_version") != REPLAY_RESULT_SCHEMA:
        raise ValueError("unsupported pre-news replay result schema")
    if replay_freeze.get("schema_version") != REPLAY_FREEZE_SCHEMA:
        raise ValueError("unsupported pre-news replay freeze schema")
    if replay_result.get("status") != "full":
        raise ValueError("industry analysis requires a full replay result")
    if replay_result.get("freeze_sha256") != replay_freeze.get("freeze_sha256"):
        raise ValueError("replay result and freeze fingerprints do not match")

    report_id = _required_text(analysis_input, "report_id")
    replay_id = _required_text(analysis_input, "replay_id")
    node_id = _required_text(analysis_input, "node_id")
    title = _required_text(analysis_input, "title")
    language = _required_text(analysis_input, "language")
    if language != "ko":
        raise ValueError("the first reader-facing industry report must use language=ko")
    if analysis_input.get("security_level_conclusion") is not False:
        raise ValueError("industry analysis must not contain a security-level conclusion")
    if replay_result.get("replay_id") != replay_id or replay_freeze.get("replay_id") != replay_id:
        raise ValueError("industry analysis replay_id does not match replay artifacts")

    input_as_of = _aware_datetime(analysis_input.get("as_of"), "analysis as_of")
    result_as_of = _aware_datetime(replay_result.get("as_of"), "replay result as_of")
    freeze_as_of = _aware_datetime(replay_freeze.get("as_of"), "replay freeze as_of")
    if input_as_of != result_as_of or input_as_of != freeze_as_of:
        raise ValueError("industry analysis as_of must exactly match replay artifacts")

    raw_rankings = replay_result.get("rankings")
    if not isinstance(raw_rankings, list):
        raise ValueError("replay rankings must be a list")
    matches = [
        item
        for item in raw_rankings
        if isinstance(item, dict) and item.get("node_id") == node_id
    ]
    if len(matches) != 1:
        raise ValueError("industry analysis node must match exactly one replay ranking")
    ranking = matches[0]
    evidence_by_id = _evidence_index(ranking, input_as_of)
    allowed_evidence_ids = set(evidence_by_id)

    executive_call = _parse_claim(
        analysis_input.get("executive_call"),
        name="executive_call",
        allowed_evidence_ids=allowed_evidence_ids,
    )
    if executive_call["claim_type"] not in {"fact", "inference"}:
        raise ValueError("executive_call must be a fact or evidence-backed inference")

    raw_sections = analysis_input.get("sections")
    if not isinstance(raw_sections, dict):
        raise ValueError("sections must be an object")
    if set(raw_sections) != set(REQUIRED_SECTIONS):
        raise ValueError("sections must contain exactly the required industry analysis sections")
    sections: dict[str, list[dict[str, object]]] = {}
    for section_name in REQUIRED_SECTIONS:
        raw_claims = raw_sections[section_name]
        if not isinstance(raw_claims, list) or not raw_claims:
            raise ValueError(f"{section_name} must contain at least one claim")
        sections[section_name] = [
            _parse_claim(
                item,
                name=f"{section_name}[{index}]",
                allowed_evidence_ids=allowed_evidence_ids,
            )
            for index, item in enumerate(raw_claims)
        ]

    raw_scores = analysis_input.get("score_explanations")
    if not isinstance(raw_scores, dict) or set(raw_scores) != set(REQUIRED_SCORE_KEYS):
        raise ValueError("score_explanations must contain exactly the six replay dimensions")
    ranking_scores = ranking.get("scores")
    if not isinstance(ranking_scores, dict) or set(ranking_scores) != set(REQUIRED_SCORE_KEYS):
        raise ValueError("replay ranking does not contain the six expected scores")
    score_explanations: dict[str, dict[str, object]] = {}
    for score_name in REQUIRED_SCORE_KEYS:
        raw = raw_scores[score_name]
        if not isinstance(raw, dict):
            raise ValueError(f"score_explanations.{score_name} must be an object")
        evidence_ids = _string_list(
            raw.get("evidence_ids"), f"score_explanations.{score_name}.evidence_ids"
        )
        unknown = sorted(set(evidence_ids) - allowed_evidence_ids)
        if unknown:
            raise ValueError(
                f"score_explanations.{score_name} references evidence outside replay: "
                + ",".join(unknown)
            )
        score_explanations[score_name] = {
            "score": ranking_scores[score_name],
            "plain_language": _required_text(raw, "plain_language", minimum=30),
            "evidence_ids": evidence_ids,
            "what_would_change": _required_text(raw, "what_would_change", minimum=20),
        }

    raw_scenarios = analysis_input.get("scenarios")
    if not isinstance(raw_scenarios, list):
        raise ValueError("scenarios must be a list")
    scenarios: list[dict[str, object]] = []
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, dict):
            raise ValueError(f"scenarios[{index}] must be an object")
        scenario_id = _required_text(raw, "scenario_id")
        evidence_ids = _string_list(raw.get("evidence_ids"), f"scenarios[{index}].evidence_ids")
        unknown = sorted(set(evidence_ids) - allowed_evidence_ids)
        if unknown:
            raise ValueError(f"scenarios[{index}] references evidence outside replay: {','.join(unknown)}")
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "label": _required_text(raw, "label"),
                "description": _required_text(raw, "description", minimum=40),
                "confirmers": _string_list(raw.get("confirmers"), f"scenarios[{index}].confirmers", allow_empty=False),
                "falsifiers": _string_list(raw.get("falsifiers"), f"scenarios[{index}].falsifiers", allow_empty=False),
                "evidence_ids": evidence_ids,
            }
        )
    if {item["scenario_id"] for item in scenarios} != REQUIRED_SCENARIOS:
        raise ValueError("scenarios must contain exactly base, upside, and downside")

    guardrails = _string_list(
        analysis_input.get("reader_guardrails"), "reader_guardrails", allow_empty=False
    )
    if len(guardrails) < 3:
        raise ValueError("reader_guardrails must contain at least three limitations")

    referenced_ids = set(executive_call["evidence_ids"])
    for claims in sections.values():
        for claim in claims:
            referenced_ids.update(claim["evidence_ids"])
    for item in score_explanations.values():
        referenced_ids.update(item["evidence_ids"])
    for scenario in scenarios:
        referenced_ids.update(scenario["evidence_ids"])
    if len(referenced_ids) < 5:
        raise ValueError("industry analysis must reference at least five replay evidence records")
    referenced_classes = {
        str(evidence_by_id[evidence_id]["evidence_class"])
        for evidence_id in referenced_ids
    }
    if len(referenced_classes) < 3:
        raise ValueError("industry analysis must use at least three evidence classes")

    report: dict[str, object] = {
        "schema_version": ANALYSIS_REPORT_SCHEMA,
        "report_id": report_id,
        "replay_id": replay_id,
        "node_id": node_id,
        "title": title,
        "language": language,
        "as_of": input_as_of.isoformat(),
        "strict_as_of": True,
        "narrative_required": True,
        "security_level_conclusion": False,
        "automatic_company_mapping": False,
        "replay_freeze_sha256": replay_freeze["freeze_sha256"],
        "analysis_input_sha256": analysis_input_sha256,
        "ranking": {
            "stage": ranking.get("stage"),
            "score": ranking.get("score"),
            "convergence_stage": ranking.get("convergence_stage"),
            "convergence_score": ranking.get("convergence_score"),
            "scores": dict(ranking_scores),
            "gate_reasons": list(ranking.get("gate_reasons", [])),
            "independent_root_shock_ids": list(
                ranking.get("independent_root_shock_ids", [])
            ),
            "path_node_sequences": list(ranking.get("path_node_sequences", [])),
        },
        "executive_call": executive_call,
        "sections": sections,
        "score_explanations": score_explanations,
        "scenarios": scenarios,
        "reader_guardrails": guardrails,
        "evidence_ledger": [evidence_by_id[key] for key in sorted(referenced_ids)],
        "evidence_reference_count": len(referenced_ids),
        "evidence_class_count": len(referenced_classes),
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def _format_evidence_ids(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "근거 ID 없음 — 불확실성 또는 조건부 시나리오"
    return ", ".join(f"`{item}`" for item in value)


def render_industry_analysis_markdown(report: dict[str, object]) -> str:
    executive = report["executive_call"]
    ranking = report["ranking"]
    sections = report["sections"]
    scores = report["score_explanations"]
    if not all(isinstance(item, dict) for item in (executive, ranking, sections, scores)):
        raise ValueError("invalid normalized industry analysis report")

    lines = [
        f"# {report['title']}",
        "",
        f"- 분석 기준시점: `{report['as_of']}`",
        f"- 경제 노드: `{report['node_id']}`",
        f"- 판정 단계: `{ranking['stage']}` / 종합점수 `{ranking['score']}`",
        f"- 인과 수렴: `{ranking['convergence_stage']}` / 수렴점수 `{ranking['convergence_score']}` / 독립 수요축 `{len(ranking['independent_root_shock_ids'])}`개",
        f"- 엄격한 시점 통제: `{str(report['strict_as_of']).lower()}`",
        "- 개별 종목 결론: 없음 — 이 보고서는 산업 노드 이해를 위한 연구 산출물입니다.",
        "",
        "## 한눈에 보는 결론",
        "",
        str(executive["text"]),
        "",
        f"- 구분: {CLAIM_TYPE_LABELS_KO[str(executive['claim_type'])]}",
        f"- 연결 근거: {_format_evidence_ids(executive['evidence_ids'])}",
    ]

    for section_name in REQUIRED_SECTIONS:
        lines.extend(["", f"## {SECTION_TITLES_KO[section_name]}", ""])
        claims = sections[section_name]
        if not isinstance(claims, list):
            raise ValueError("invalid normalized section claims")
        for claim in claims:
            if not isinstance(claim, dict):
                raise ValueError("invalid normalized claim")
            lines.extend(
                [
                    f"### {claim['label']}",
                    "",
                    str(claim["text"]),
                    "",
                    f"- 구분: {CLAIM_TYPE_LABELS_KO[str(claim['claim_type'])]}",
                    f"- 연결 근거: {_format_evidence_ids(claim['evidence_ids'])}",
                    "",
                ]
            )

    lines.extend(
        [
            "## 점수를 사람의 언어로 해석하기",
            "",
            "이 점수는 수익률 확률이나 매수 신호가 아닙니다. 현재 cutoff 이전에 확보된 근거가 각 질문에 얼마나 답하고 있는지를 압축한 보조 지표입니다.",
            "",
            "| 평가 항목 | 점수 | 현재 의미 | 판단을 바꿀 추가 증거 |",
            "|---|---:|---|---|",
        ]
    )
    for score_name in REQUIRED_SCORE_KEYS:
        item = scores[score_name]
        if not isinstance(item, dict):
            raise ValueError("invalid normalized score explanation")
        plain = str(item["plain_language"]).replace("|", "\\|").replace("\n", " ")
        change = str(item["what_would_change"]).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {SCORE_TITLES_KO[score_name]} | {item['score']}/5 | {plain} | {change} |"
        )

    lines.extend(["", "## 세 가지 조건부 경로", ""])
    for scenario in report["scenarios"]:
        if not isinstance(scenario, dict):
            raise ValueError("invalid normalized scenario")
        lines.extend(
            [
                f"### {scenario['label']}",
                "",
                str(scenario["description"]),
                "",
                "- 확인 신호: " + "; ".join(str(item) for item in scenario["confirmers"]),
                "- 반증 신호: " + "; ".join(str(item) for item in scenario["falsifiers"]),
                f"- 연결 근거: {_format_evidence_ids(scenario['evidence_ids'])}",
                "",
            ]
        )

    lines.extend(["## 이 보고서를 읽을 때의 제한", ""])
    for guardrail in report["reader_guardrails"]:
        lines.append(f"- {guardrail}")

    lines.extend(
        [
            "",
            "## 근거 원장",
            "",
            "| 근거 ID | 근거 유형 | 관측일 | 출처 |",
            "|---|---|---|---|",
        ]
    )
    for item in report["evidence_ledger"]:
        if not isinstance(item, dict):
            raise ValueError("invalid normalized evidence ledger")
        source = str(item["source_id"]).replace("|", "\\|")
        lines.append(
            f"| `{item['evidence_id']}` | `{item['evidence_class']}` | "
            f"`{item['observed_at']}` | {source} |"
        )
    lines.extend(
        [
            "",
            f"보고서 해시: `{report['report_sha256']}`",
            f"Replay freeze: `{report['replay_freeze_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_industry_analysis_artifacts(
    output_dir: Path, report: dict[str, object]
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "industry_analysis.json"
    markdown_path = output_dir / "industry_analysis.ko.md"
    payloads = (
        (
            json_path,
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        ),
        (markdown_path, render_industry_analysis_markdown(report)),
    )
    for path, content in payloads:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    return json_path, markdown_path
