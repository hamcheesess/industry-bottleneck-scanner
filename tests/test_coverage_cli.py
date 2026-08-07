import json

import pytest

from industry_bottleneck_scanner import coverage_cli
from industry_bottleneck_scanner.transcript_coverage import CoverageResult, CoverageSummary


def test_cli_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="ALPHA_VANTAGE_API_KEY"):
        coverage_cli.main(["--quarter", "2026Q2"])


def test_cli_writes_summary_without_api_key_or_transcript_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "secret-test-key")

    def fake_evaluate(source, *, tickers, quarter, max_requests):
        assert source.api_key == "secret-test-key"
        assert max_requests == 5
        return CoverageSummary(
            requested=5,
            available=3,
            missing=1,
            errors=1,
            results=(
                CoverageResult("AAPL", quarter, "available", turn_count=25),
                CoverageResult("MSFT", quarter, "available", turn_count=31),
                CoverageResult("ETN", quarter, "available", turn_count=18),
                CoverageResult("POWL", quarter, "missing"),
                CoverageResult("NVT", quarter, "error", error="rate limited"),
            ),
        )

    monkeypatch.setattr(coverage_cli, "evaluate_coverage", fake_evaluate)
    output = tmp_path / "coverage.json"
    assert coverage_cli.main(["--quarter", "2026Q2", "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["requested"] == 5
    assert payload["available"] == 3
    assert payload["availability_rate"] == 0.6
    assert "secret-test-key" not in text
    assert "transcript" not in text.casefold()


def test_cli_enforces_sample_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test")
    with pytest.raises(SystemExit, match="exceeds sample size"):
        coverage_cli.main(
            ["--quarter", "2026Q2", "--limit", "20", "--tickers", "AAPL", "MSFT"]
        )
