from __future__ import annotations

import json
from pathlib import Path

import pytest

from industry_bottleneck_scanner.root_shock_research_adjudication import (
    adjudicate_root_shock_research,
)
from industry_bottleneck_scanner.root_shock_research_adjudication_cli import main
from industry_bottleneck_scanner.root_shock_cli import main as append_root_shock


AS_OF = "2026-08-21T23:59:59+00:00"
PACKET_ID = "packet-20260821-machinery"


def _write_packet(tmp_path: Path) -> Path:
    packet = {
        "schema_version": "root-shock-research-packet-v1",
        "packet_id": PACKET_ID,
        "as_of": AS_OF,
        "strict_as_of": True,
        "approval_ready": False,
        "market_trigger_id": "market-trigger:2026-08-21:machinery",
        "bucket": "SIC 3560 — GENERAL INDUSTRIAL MACHINERY & EQUIPMENT",
        "direct_evidence": [
            {
                "signal_id": "signal-a",
                "company_id": "cik-0000000001",
                "ticker": "MACH",
                "published_at": "2026-08-10T12:00:00+00:00",
                "source_url": "https://www.sec.gov/Archives/signal-a.htm",
            }
        ],
    }
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(packet) + "\n")
    return path


def _valid_result() -> dict[str, object]:
    return {
        "schema_version": "root-shock-research-result-v1",
        "packet_id": PACKET_ID,
        "as_of": AS_OF,
        "root_shock": {
            "root_shock_id": "data-center-power-buildout-2026q3",
            "root_node": "data-center-power-infrastructure-demand",
            "label": "Data-center power infrastructure buildout",
            "mechanism": (
                "Large compute deployments raised committed electrical load, causing utilities "
                "and operators to accelerate orders for constrained power infrastructure."
            ),
            "causal_chain": [
                "compute capacity commitments increase facility electrical load",
                "higher committed load advances power-infrastructure procurement",
            ],
            "detected_at": "2026-08-20T12:00:00+00:00",
            "demand_strength": 4,
            "evidence": [
                {
                    "evidence_id": "issuer-backlog",
                    "evidence_class": "backlog_or_orders",
                    "source_category": "issuer_operating_disclosure",
                    "packet_signal_id": "signal-a",
                    "summary": "Issuer reported firm backlog growth tied to customer orders.",
                },
                {
                    "evidence_id": "government-load-data",
                    "evidence_class": "physical_industry_data",
                    "source_category": "government_statistic",
                    "source_id": "government-load-series-2026-08",
                    "source_url": "https://www.energy.gov/example/load-series",
                    "observed_at": "2026-08-15T12:00:00+00:00",
                    "summary": "Government data showed an increase in committed large-load demand.",
                },
            ],
        },
    }


def _write_result(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload) + "\n")
    return path


def test_validates_eligible_research_without_appending(tmp_path: Path) -> None:
    packet = _write_packet(tmp_path)
    research = _write_result(tmp_path, _valid_result())
    output = tmp_path / "out"
    result = adjudicate_root_shock_research(
        packet_path=packet,
        research_result_path=research,
        output_dir=output,
    )

    assert result["approval_eligible"] is True
    assert result["append_performed"] is False
    assert result["reasons"] == []
    assert set(result["evidence_classes"]) == {"backlog_or_orders", "physical_industry_data"}
    assert result["source_entity_count"] == 2
    root_input = json.loads((output / "root_shock_input.json").read_text())
    assert root_input["schema_version"] == "root-demand-shock-input-v1"
    assert root_input["market_trigger_id"] == "market-trigger:2026-08-21:machinery"
    assert root_input["market_bucket"].startswith("SIC 3560")


def test_ineligible_result_writes_non_appendable_schema(tmp_path: Path) -> None:
    packet = _write_packet(tmp_path)
    payload = _valid_result()
    payload["root_shock"]["evidence"] = [payload["root_shock"]["evidence"][0]]
    research = _write_result(tmp_path, payload)
    output = tmp_path / "out"
    result = adjudicate_root_shock_research(
        packet_path=packet,
        research_result_path=research,
        output_dir=output,
    )

    assert result["approval_eligible"] is False
    assert "non_issuer_source_required" in result["reasons"]
    root_input = json.loads((output / "root_shock_input.json").read_text())
    assert root_input["schema_version"] == "root-demand-shock-input-ineligible-v1"
    assert root_input["ineligible_reasons"] == result["reasons"]
    with pytest.raises(SystemExit, match="unsupported root-shock input schema"):
        append_root_shock(
            [
                "--input",
                str(output / "root_shock_input.json"),
                "--registry",
                str(tmp_path / "roots.jsonl"),
            ]
        )


def test_rejects_post_cutoff_external_evidence(tmp_path: Path) -> None:
    packet = _write_packet(tmp_path)
    payload = _valid_result()
    payload["root_shock"]["evidence"][1]["observed_at"] = "2026-08-22T00:00:00+00:00"
    research = _write_result(tmp_path, payload)
    with pytest.raises(ValueError, match="look-ahead research evidence"):
        adjudicate_root_shock_research(
            packet_path=packet,
            research_result_path=research,
            output_dir=tmp_path / "out",
        )


def test_rejects_packet_identity_and_ticker_node(tmp_path: Path) -> None:
    packet = _write_packet(tmp_path)
    mismatch = _valid_result()
    mismatch["packet_id"] = "other-packet"
    with pytest.raises(ValueError, match="packet_id does not match"):
        adjudicate_root_shock_research(
            packet_path=packet,
            research_result_path=_write_result(tmp_path, mismatch),
            output_dir=tmp_path / "out-a",
        )

    ticker_node = _valid_result()
    ticker_node["root_shock"]["root_node"] = "mach"
    with pytest.raises(ValueError, match="stable lowercase economic-node ID"):
        adjudicate_root_shock_research(
            packet_path=packet,
            research_result_path=_write_result(tmp_path, ticker_node),
            output_dir=tmp_path / "out-b",
        )


def test_cli_reports_eligible_without_append(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    packet = _write_packet(tmp_path)
    research = _write_result(tmp_path, _valid_result())
    assert (
        main(
            [
                "--packet",
                str(packet),
                "--research-result",
                str(research),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "approval_eligible=true" in output
    assert "append_performed=false" in output
