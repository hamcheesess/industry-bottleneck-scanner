from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request

import pytest

from industry_bottleneck_scanner.models import Classification
from industry_bottleneck_scanner.sec_edgar import (
    SecEdgarClient,
    SecEdgarError,
    SecIssuer,
    collect_sec_disclosures,
    html_to_sections,
)


AS_OF = datetime(2026, 8, 21, 23, 59, tzinfo=timezone.utc)
CIK = "0000123456"
ACCESSION = "0000123456-26-000001"


def filing_columns(*, acceptance: str = "2026-08-01T16:05:00.000Z") -> dict[str, list[object]]:
    return {
        "accessionNumber": [ACCESSION],
        "filingDate": ["2026-08-01"],
        "acceptanceDateTime": [acceptance],
        "form": ["8-K"],
        "primaryDocument": ["form8-k.htm"],
        "primaryDocDescription": ["Current report"],
    }


def submissions_payload(*, recent: dict[str, list[object]] | None = None) -> bytes:
    return json.dumps(
        {
            "cik": CIK,
            "filings": {
                "recent": recent or filing_columns(),
                "files": [],
            },
        }
    ).encode()


def index_html() -> bytes:
    return b"""
    <html><body><table>
      <tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
      <tr><td>1</td><td>Current report</td><td><a href="/ix?doc=/Archives/edgar/data/123456/filing/form8-k.htm">form8-k.htm</a></td><td>8-K</td><td>1000</td></tr>
      <tr><td>2</td><td>Earnings release</td><td><a href="earnings.htm">earnings.htm</a></td><td>EX-99.1</td><td>2000</td></tr>
      <tr><td>3</td><td>Image</td><td><a href="logo.jpg">logo.jpg</a></td><td>GRAPHIC</td><td>50</td></tr>
    </table></body></html>
    """


class FixtureTransport:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.requests: list[Request] = []

    def __call__(self, request: Request) -> bytes:
        self.requests.append(request)
        try:
            return self.responses[request.full_url]
        except KeyError as exc:
            raise AssertionError(f"unexpected SEC request: {request.full_url}") from exc


def urls() -> dict[str, str]:
    directory = f"https://www.sec.gov/Archives/edgar/data/123456/{ACCESSION.replace('-', '')}/"
    return {
        "submissions": f"https://data.sec.gov/submissions/CIK{CIK}.json",
        "index": f"{directory}{ACCESSION}-index.htm",
        "primary": f"{directory}form8-k.htm",
        "exhibit": f"{directory}earnings.htm",
    }


def test_sec_client_requires_declared_contact_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="organization and contact email"):
        SecEdgarClient(user_agent="anonymous-bot", cache_dir=tmp_path)


def test_collects_primary_filing_and_earnings_exhibit_with_strict_provenance(tmp_path: Path) -> None:
    locations = urls()
    transport = FixtureTransport(
        {
            locations["submissions"]: submissions_payload(),
            locations["index"]: index_html(),
            locations["primary"]: b"<html><body><p>Capacity expansion remains on schedule.</p></body></html>",
            locations["exhibit"]: b"<html><body><h1>Results</h1><p>Backlog reached a record level.</p></body></html>",
        }
    )
    client = SecEdgarClient(
        user_agent="Bottleneck Research admin@example.com",
        cache_dir=tmp_path,
        request_interval_seconds=0.1,
        transport=transport,
    )

    result = collect_sec_disclosures(
        client,
        issuers=(
            SecIssuer(
                company_id=f"cik-{CIK}",
                cik=CIK,
                ticker="TEST",
                classification=Classification(industry="Electrical Equipment"),
            ),
        ),
        since=date(2024, 11, 1),
        as_of=AS_OF,
        retrieved_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )

    assert [item.document_type for item in result.disclosures] == ["sec_8k", "sec_8k_exhibit"]
    assert result.disclosures[1].provider_document_id == f"{ACCESSION}:earnings.htm"
    assert result.disclosures[1].source_url == locations["exhibit"]
    assert "Backlog reached a record level" in result.disclosures[1].sections[0].text
    assert result.diagnostics.provider_requests == 4
    assert all(request.get_header("User-agent") == "Bottleneck Research admin@example.com" for request in transport.requests)

    second = collect_sec_disclosures(
        client,
        issuers=(SecIssuer(company_id=f"cik-{CIK}", cik=CIK),),
        since=date(2024, 11, 1),
        as_of=AS_OF,
    )
    assert second.diagnostics.provider_requests == 4
    assert second.diagnostics.cache_hits == 4


def test_loads_overlapping_additional_submission_history(tmp_path: Path) -> None:
    locations = urls()
    older_name = f"CIK{CIK}-submissions-001.json"
    root = json.loads(submissions_payload(recent={key: [] for key in filing_columns()}))
    root["filings"]["files"] = [
        {"name": older_name, "filingFrom": "2024-01-01", "filingTo": "2025-12-31"}
    ]
    transport = FixtureTransport(
        {
            locations["submissions"]: json.dumps(root).encode(),
            f"https://data.sec.gov/submissions/{older_name}": json.dumps(filing_columns()).encode(),
        }
    )
    client = SecEdgarClient(
        user_agent="Bottleneck Research admin@example.com",
        cache_dir=tmp_path,
        request_interval_seconds=0.1,
        transport=transport,
    )

    filings = client.filings(cik=CIK, since=date(2024, 11, 1), as_of=AS_OF)

    assert [item.accession_number for item in filings] == [ACCESSION]
    assert len(transport.requests) == 2


def test_filing_accepted_after_as_of_is_excluded(tmp_path: Path) -> None:
    locations = urls()
    transport = FixtureTransport(
        {
            locations["submissions"]: submissions_payload(
                recent=filing_columns(acceptance="2026-08-22T00:00:00.000Z")
            )
        }
    )
    client = SecEdgarClient(
        user_agent="Bottleneck Research admin@example.com",
        cache_dir=tmp_path,
        request_interval_seconds=0.1,
        transport=transport,
    )

    assert client.filings(cik=CIK, since=date(2024, 11, 1), as_of=AS_OF) == ()


def test_html_normalizer_discards_non_visible_content_and_chunks() -> None:
    sections = html_to_sections(
        b"<html><head><style>hidden</style></head><body><p>Visible backlog.</p><script>secret()</script><p>Capacity constrained.</p></body></html>",
        max_section_characters=25,
    )

    assert [item.text for item in sections] == ["Visible backlog.", "Capacity constrained."]
    assert "hidden" not in " ".join(item.text for item in sections)
    assert "secret" not in " ".join(item.text for item in sections)

    oversized = html_to_sections(b"<p>alpha beta gamma</p>", max_section_characters=10)
    assert [item.text for item in oversized] == ["alpha beta", "gamma"]


def test_client_rejects_unexpected_provider_host(tmp_path: Path) -> None:
    client = SecEdgarClient(
        user_agent="Bottleneck Research admin@example.com",
        cache_dir=tmp_path,
        request_interval_seconds=0.1,
        transport=FixtureTransport({}),
    )
    with pytest.raises(SecEdgarError, match="unexpected provider URL"):
        client._get("https://example.com/filing.json")


def test_open_request_classifies_socket_read_timeout_as_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> object:
        raise TimeoutError("read operation timed out")

    monkeypatch.setattr("industry_bottleneck_scanner.sec_edgar.urlopen", timeout)
    with pytest.raises(SecEdgarError, match="transport error: read operation timed out"):
        SecEdgarClient._open_request(Request("https://data.sec.gov/submissions/test.json"))
