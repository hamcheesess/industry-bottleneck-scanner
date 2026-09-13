from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import get_args
from urllib.parse import urlsplit

from .causal_expansion import CausalEvidence, EvidenceClass
from .root_demand_shock import (
    RootDemandShock,
    evaluate_root_demand_shock,
)


RESULT_SCHEMA_VERSION = "root-shock-research-result-v1"
ADJUDICATION_SCHEMA_VERSION = "root-shock-research-adjudication-v1"
ELIGIBLE_INPUT_SCHEMA_VERSION = "root-demand-shock-input-v1"
INELIGIBLE_INPUT_SCHEMA_VERSION = "root-demand-shock-input-ineligible-v1"
NODE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
VALID_EVIDENCE_CLASSES = set(get_args(EvidenceClass))
VALID_SOURCE_CATEGORIES = {
    "issuer_operating_disclosure",
    "customer_disclosure",
    "supplier_disclosure",
    "competitor_disclosure",
    "physical_industry_data",
    "government_statistic",
    "regulatory_record",
    "industry_association_data",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _aware_datetime(value: object, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return parsed


def _required_text(payload: dict[str, object], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def _stable_node(value: str, *, field: str, forbidden: set[str]) -> str:
    if not NODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a stable lowercase economic-node ID")
    if value.startswith("cik-") or value.casefold() in forbidden:
        raise ValueError(f"{field} must not be an issuer or ticker identity")
    return value


def _source_url(value: object, *, field: str) -> str:
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be an absolute HTTP(S) URL")
    return url


def _causal_evidence(
    raw: dict[str, object],
    *,
    packet_evidence: dict[str, dict[str, object]],
    as_of: datetime,
) -> tuple[CausalEvidence, dict[str, object]]:
    evidence_id = _required_text(raw, "evidence_id")
    evidence_class = _required_text(raw, "evidence_class")
    if evidence_class not in VALID_EVIDENCE_CLASSES:
        raise ValueError(f"unsupported causal evidence class: {evidence_class}")
    source_category = _required_text(raw, "source_category")
    if source_category not in VALID_SOURCE_CATEGORIES:
        raise ValueError(f"unsupported source category: {source_category}")
    summary = _required_text(raw, "summary")

    packet_signal_id = raw.get("packet_signal_id")
    if source_category == "issuer_operating_disclosure":
        if packet_signal_id is None or str(packet_signal_id) not in packet_evidence:
            raise ValueError("issuer evidence must reference a selected packet signal")
        selected = packet_evidence[str(packet_signal_id)]
        observed_at = _aware_datetime(selected["published_at"], field="packet signal published_at")
        source_url = _source_url(selected["source_url"], field="packet signal source_url")
        source_id = f"packet-signal:{packet_signal_id}"
        beneficiary_company_id = str(selected["company_id"])
        source_company_id = beneficiary_company_id
    else:
        if packet_signal_id is not None:
            raise ValueError("non-issuer evidence must not claim a packet signal")
        observed_at = _aware_datetime(raw.get("observed_at"), field="evidence observed_at")
        source_url = _source_url(raw.get("source_url"), field="evidence source_url")
        source_id = _required_text(raw, "source_id")
        beneficiary_company_id = (
            None
            if raw.get("beneficiary_company_id") is None
            else str(raw["beneficiary_company_id"])
        )
        source_company_id = (
            None if raw.get("source_company_id") is None else str(raw["source_company_id"])
        )
    if observed_at > as_of:
        raise ValueError(f"look-ahead research evidence is forbidden: {evidence_id}")

    evidence = CausalEvidence(
        evidence_id=evidence_id,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        source_id=source_id,
        observed_at=observed_at,
        summary=summary,
        beneficiary_company_id=beneficiary_company_id,
        source_company_id=source_company_id,
    )
    provenance = {
        "evidence_id": evidence_id,
        "evidence_class": evidence_class,
        "source_category": source_category,
        "source_id": source_id,
        "source_url": source_url,
        "observed_at": observed_at.isoformat(),
        "packet_signal_id": packet_signal_id,
        "packet_excerpt": (
            selected.get("excerpt")
            if source_category == "issuer_operating_disclosure"
            else None
        ),
        "externally_corroborating": evidence.externally_corroborating,
    }
    return evidence, provenance


def _root_shock_input(shock: RootDemandShock, *, schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "root_shock_id": shock.root_shock_id,
        "root_node": shock.root_node,
        "label": shock.label,
        "mechanism": shock.mechanism,
        "market_trigger_id": shock.market_trigger_id,
        "market_bucket": shock.market_bucket,
        "detected_at": shock.detected_at.isoformat(),
        "as_of": shock.as_of.isoformat(),
        "demand_strength": shock.demand_strength,
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
            for item in shock.evidence
        ],
    }


def adjudicate_root_shock_research(
    *,
    packet_path: Path,
    research_result_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Validate a research proposal without appending or changing an approval registry."""

    packet = _load_object(packet_path)
    if packet.get("schema_version") != "root-shock-research-packet-v1":
        raise ValueError("unsupported root-shock research packet schema")
    if packet.get("strict_as_of") is not True:
        raise ValueError("research packet must be strict-as-of")
    if packet.get("approval_ready") is not False:
        raise ValueError("research packet must enter adjudication fail-closed")
    result = _load_object(research_result_path)
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise ValueError("unsupported root-shock research result schema")
    if result.get("packet_id") != packet.get("packet_id"):
        raise ValueError("research result packet_id does not match")
    if result.get("as_of") != packet.get("as_of"):
        raise ValueError("research result as_of does not match packet")

    as_of = _aware_datetime(packet["as_of"], field="packet as_of")
    raw_shock = result.get("root_shock")
    if not isinstance(raw_shock, dict):
        raise ValueError("research result requires a root_shock object")
    direct_evidence = packet.get("direct_evidence")
    if not isinstance(direct_evidence, list):
        raise ValueError("research packet direct_evidence must be a list")
    packet_evidence = {
        str(item["signal_id"]): item for item in direct_evidence if isinstance(item, dict)
    }
    if len(packet_evidence) != len(direct_evidence):
        raise ValueError("research packet contains duplicate or invalid direct evidence")
    forbidden = {
        str(item.get("ticker") or "").casefold()
        for item in direct_evidence
        if isinstance(item, dict) and item.get("ticker")
    }
    forbidden.update(
        str(item.get("company_id") or "").casefold()
        for item in direct_evidence
        if isinstance(item, dict)
    )
    root_shock_id = _stable_node(
        _required_text(raw_shock, "root_shock_id"),
        field="root_shock_id",
        forbidden=forbidden,
    )
    root_node = _stable_node(
        _required_text(raw_shock, "root_node"),
        field="root_node",
        forbidden=forbidden,
    )
    mechanism = _required_text(raw_shock, "mechanism")
    causal_chain_raw = raw_shock.get("causal_chain")
    if not isinstance(causal_chain_raw, list):
        raise ValueError("causal_chain must be a list")
    causal_chain = tuple(str(item).strip() for item in causal_chain_raw if str(item).strip())
    raw_evidence = raw_shock.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("root_shock evidence must be a list")
    evidence_pairs = [
        _causal_evidence(item, packet_evidence=packet_evidence, as_of=as_of)
        for item in raw_evidence
        if isinstance(item, dict)
    ]
    if len(evidence_pairs) != len(raw_evidence):
        raise ValueError("root_shock evidence rows must be objects")
    evidence = tuple(item[0] for item in evidence_pairs)
    provenance = [item[1] for item in evidence_pairs]
    if len({item.evidence_id for item in evidence}) != len(evidence):
        raise ValueError("root_shock evidence_id values must be unique")
    detected_at = _aware_datetime(raw_shock.get("detected_at"), field="detected_at")
    demand_strength = raw_shock.get("demand_strength")
    if isinstance(demand_strength, bool) or not isinstance(demand_strength, int):
        raise ValueError("demand_strength must be an integer from 0 to 5")
    shock = RootDemandShock(
        root_shock_id=root_shock_id,
        root_node=root_node,
        label=_required_text(raw_shock, "label"),
        mechanism=mechanism,
        market_trigger_id=str(packet["market_trigger_id"]),
        market_bucket=str(packet["bucket"]),
        detected_at=detected_at,
        as_of=as_of,
        demand_strength=demand_strength,
        evidence=evidence,
    )
    approval = evaluate_root_demand_shock(shock)
    source_categories = {str(item["source_category"]) for item in provenance}
    source_ids = {str(item["source_id"]) for item in provenance}
    packet_signal_ids = {
        str(item["packet_signal_id"])
        for item in provenance
        if item.get("packet_signal_id") is not None
    }
    research_reasons: list[str] = list(approval.reasons)
    if len(mechanism) < 60 or len(set(causal_chain)) < 2:
        research_reasons.append("concrete_causal_mechanism_required")
    if not packet_signal_ids:
        research_reasons.append("packet_operating_evidence_not_linked")
    if source_categories <= {"issuer_operating_disclosure"}:
        research_reasons.append("non_issuer_source_required")
    if len(source_ids) < 2:
        research_reasons.append("insufficient_source_entity_diversity")
    reasons = tuple(sorted(set(research_reasons)))
    eligible = not reasons

    input_schema = ELIGIBLE_INPUT_SCHEMA_VERSION if eligible else INELIGIBLE_INPUT_SCHEMA_VERSION
    root_input = _root_shock_input(shock, schema_version=input_schema)
    if not eligible:
        root_input["ineligible_reasons"] = list(reasons)
    root_input_path = output_dir / "root_shock_input.json"
    _atomic_json(root_input_path, root_input)

    adjudication: dict[str, object] = {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "packet_id": packet["packet_id"],
        "as_of": packet["as_of"],
        "strict_as_of": True,
        "provider_specific_code_used": False,
        "approval_eligible": eligible,
        "append_performed": False,
        "reasons": list(reasons),
        "evidence_classes": list(approval.evidence_classes),
        "source_categories": sorted(source_categories),
        "source_entity_count": len(source_ids),
        "linked_packet_signal_ids": sorted(packet_signal_ids),
        "causal_chain": list(causal_chain),
        "provenance": provenance,
        "root_shock_input": str(root_input_path),
        "root_shock_input_schema": input_schema,
        "inputs": {
            "research_packet": str(packet_path),
            "research_packet_sha256": _sha256(packet_path),
            "research_result": str(research_result_path),
            "research_result_sha256": _sha256(research_result_path),
        },
    }
    _atomic_json(output_dir / "research_adjudication.json", adjudication)
    return adjudication
