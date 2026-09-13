import json

import pytest

from industry_bottleneck_scanner.operating_evidence_cli import main


def disclosure(company_id: str, ticker: str, published_at: str) -> dict:
    return {
        "provider": "sec_edgar",
        "provider_document_id": f"accession-{company_id}",
        "company_id": company_id,
        "ticker": ticker,
        "document_type": "sec_8k_exhibit",
        "published_at": published_at,
        "retrieved_at": "2026-08-21T10:00:00+00:00",
        "source_url": f"https://www.sec.gov/Archives/{company_id}.htm",
        "classification": {"industry": "Electrical Equipment"},
        "sections": [
            {
                "section_id": "release",
                "source_section": "results",
                "text": "Backlog reached a record level and capacity remains constrained.",
            }
        ],
    }


def test_operating_evidence_cli_writes_manifest_signals_and_support(tmp_path, capsys) -> None:
    disclosures = tmp_path / "disclosures.jsonl"
    disclosures.write_text(
        "\n".join(
            json.dumps(disclosure(company, ticker, "2026-08-10T20:00:00+00:00"))
            for company, ticker in (("issuer-a", "AAA"), ("issuer-b", "BBB"))
        )
        + "\n"
    )
    companies = tmp_path / "companies.csv"
    companies.write_text("company_id\nissuer-a\nissuer-b\nissuer-c\n")
    output = tmp_path / "output"

    assert main(
        [
            "--disclosures-jsonl",
            str(disclosures),
            "--expected-companies-csv",
            str(companies),
            "--bucket",
            "Electrical Equipment",
            "--as-of",
            "2026-08-21T20:00:00+00:00",
            "--output-dir",
            str(output),
        ]
    ) == 0

    manifest = json.loads((output / "source_documents.json").read_text())
    support = json.loads((output / "operating_support.json").read_text())
    signals = [json.loads(line) for line in (output / "atomic_signals.jsonl").read_text().splitlines()]
    assert manifest["schema_version"] == "source-document-manifest-v1"
    assert manifest["document_count"] == 2
    assert "text" not in manifest["documents"][0]
    assert manifest["documents"][0]["content_fingerprint"]
    assert support["schema_version"] == "operating-support-v1"
    assert support["stage"] == "one_sided_strengthening"
    assert support["fresh_coverage_ratio"] == pytest.approx(2 / 3, abs=0.000001)
    assert {item["metric"] for item in signals} >= {"backlog_strength", "capacity_constraint"}
    assert "stage=one_sided_strengthening" in capsys.readouterr().out


def test_operating_evidence_cli_rejects_future_disclosure(tmp_path) -> None:
    disclosures = tmp_path / "disclosures.jsonl"
    disclosures.write_text(
        json.dumps(disclosure("issuer-a", "AAA", "2026-08-22T20:00:00+00:00")) + "\n"
    )
    companies = tmp_path / "companies.csv"
    companies.write_text("company_id\nissuer-a\n")

    with pytest.raises(ValueError, match="later than as_of"):
        main(
            [
                "--disclosures-jsonl",
                str(disclosures),
                "--expected-companies-csv",
                str(companies),
                "--bucket",
                "Electrical Equipment",
                "--as-of",
                "2026-08-21T20:00:00+00:00",
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )
