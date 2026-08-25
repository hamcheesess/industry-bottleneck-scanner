from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from industry_bottleneck_scanner.disclosure_documents import DisclosureSection, PublicDisclosure
from industry_bottleneck_scanner.sec_edgar import (
    SecCollectionDiagnostics,
    SecDisclosureCollection,
    SecEdgarError,
)
from industry_bottleneck_scanner.sec_edgar_cli import main


def write_companies(path: Path, rows: tuple[str, ...] = ("cik-0000123456,123456,TEST,Industrials,Electrical Equipment",)) -> None:
    path.write_text(
        "company_id,cik,ticker,sector,bucket\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def args(tmp_path: Path) -> list[str]:
    companies = tmp_path / "companies.csv"
    write_companies(companies)
    return [
        "--companies-csv",
        str(companies),
        "--since",
        "2024-11-01",
        "--as-of",
        "2026-08-21T23:59:00+00:00",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--output-jsonl",
        str(tmp_path / "disclosures.jsonl"),
        "--diagnostics",
        str(tmp_path / "diagnostics.json"),
    ]


def test_sec_collection_cli_writes_replayable_disclosure_and_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    def fake_collect(client: object, **kwargs: object) -> SecDisclosureCollection:
        captured["issuers"] = kwargs["issuers"]
        published = datetime(2026, 8, 1, 16, 5, tzinfo=timezone.utc)
        return SecDisclosureCollection(
            disclosures=(
                PublicDisclosure(
                    provider="sec_edgar",
                    provider_document_id="accession:earnings.htm",
                    company_id="cik-0000123456",
                    ticker="TEST",
                    document_type="sec_8k_exhibit",
                    published_at=published,
                    retrieved_at=published,
                    source_url="https://www.sec.gov/Archives/example/earnings.htm",
                    sections=(
                        DisclosureSection(section_id="section-0001", text="Backlog is at a record."),
                    ),
                ),
            ),
            diagnostics=SecCollectionDiagnostics(
                issuer_count=1,
                filing_count=1,
                disclosure_count=1,
                skipped_unsupported_documents=0,
                provider_requests=3,
                cache_hits=0,
            ),
        )

    monkeypatch.setenv("SEC_USER_AGENT", "Bottleneck Research admin@example.com")
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.SecEdgarClient", FakeClient)
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.collect_sec_disclosures", fake_collect)

    assert main(args(tmp_path)) == 0

    disclosure = json.loads((tmp_path / "disclosures.jsonl").read_text(encoding="utf-8"))
    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert disclosure["provider_document_id"] == "accession:earnings.htm"
    assert disclosure["sections"][0]["text"] == "Backlog is at a record."
    assert diagnostics["schema_version"] == "sec-edgar-collection-v1"
    assert diagnostics["status"] == "complete"
    assert diagnostics["provider_requests"] == 3
    assert captured["user_agent"] == "Bottleneck Research admin@example.com"
    issuers = captured["issuers"]
    assert issuers[0].classification.industry == "Electrical Equipment"


def test_sec_collection_cli_requires_user_agent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(SystemExit, match="SEC_USER_AGENT is required"):
        main(args(tmp_path))


def test_sec_collection_cli_fails_instead_of_silently_truncating(tmp_path: Path) -> None:
    invocation = args(tmp_path)
    companies = Path(invocation[1])
    write_companies(
        companies,
        rows=(
            "cik-0000123456,123456,AAA,Industrials,Electrical Equipment",
            "cik-0000654321,654321,BBB,Industrials,Electrical Equipment",
        ),
    )
    invocation.extend(["--max-issuers", "1"])
    with pytest.raises(SystemExit, match="exceeds --max-issuers"):
        main(invocation)


@pytest.mark.parametrize(
    ("message", "expected_kind"),
    (
        ("SEC EDGAR HTTP 403 (fair-access identity or pacing may be rejected)", "sec_access_policy"),
        ("SEC EDGAR HTTP 429 (fair-access identity or pacing may be rejected)", "sec_rate_limit"),
        ("SEC EDGAR transport error: timeout", "sec_transport"),
        ("SEC EDGAR returned invalid JSON", "sec_response_contract"),
    ),
)
def test_sec_collection_cli_persists_classified_failure_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    message: str,
    expected_kind: str,
) -> None:
    class FakeClient:
        provider_requests = 2
        cache_hits = 1

        def __init__(self, **kwargs: object) -> None:
            pass

    def fail(*args: object, **kwargs: object) -> SecDisclosureCollection:
        raise SecEdgarError(message)

    monkeypatch.setenv("SEC_USER_AGENT", "Bottleneck Research admin@example.com")
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.SecEdgarClient", FakeClient)
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.collect_sec_disclosures", fail)

    invocation = args(tmp_path)
    with pytest.raises(SystemExit, match=expected_kind):
        main(invocation)
    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["status"] == "failed"
    assert diagnostics["failure_kind"] == expected_kind
    assert diagnostics["provider_requests"] == 2
    assert diagnostics["cache_hits"] == 1


def test_sec_collection_cli_marks_partial_document_gaps_without_failing_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

    def partial(*args: object, **kwargs: object) -> SecDisclosureCollection:
        return SecDisclosureCollection(
            disclosures=(
                PublicDisclosure(
                    provider="sec_edgar",
                        provider_document_id="accession:filing.htm",
                        company_id="cik-0000123456",
                        ticker=None,
                    document_type="sec_10q",
                    published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                    retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
                    source_url="https://www.sec.gov/Archives/example/filing.htm",
                    sections=(DisclosureSection("section-0001", "Capacity remains tight."),),
                ),
            ),
            diagnostics=SecCollectionDiagnostics(
                issuer_count=1,
                filing_count=2,
                disclosure_count=1,
                skipped_unsupported_documents=0,
                provider_requests=3,
                cache_hits=0,
                failed_document_count=1,
                failures=("document:cik-0000123456:timeout",),
            ),
        )

    monkeypatch.setenv("SEC_USER_AGENT", "Bottleneck Research admin@example.com")
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.SecEdgarClient", FakeClient)
    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar_cli.collect_sec_disclosures", partial)
    assert main(args(tmp_path)) == 0
    diagnostics = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["status"] == "complete_with_gaps"
    assert diagnostics["failed_document_count"] == 1
