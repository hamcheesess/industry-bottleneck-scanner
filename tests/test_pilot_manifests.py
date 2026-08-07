from pathlib import Path

from industry_bottleneck_scanner.company_metadata import load_company_period_metadata_csv
from industry_bottleneck_scanner.transcript_collection import TranscriptRequest


def _request_pairs(path: Path) -> set[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()[1:]
    return {
        (request.ticker, request.quarter)
        for line in lines
        if line.strip()
        for request in (TranscriptRequest(*line.split(",", 1)),)
    }


def test_power_infrastructure_pilot_manifests_are_matched_and_dated() -> None:
    root = Path("experiments")
    requests = _request_pairs(root / "pilot_power_infrastructure_requests.csv")
    current = load_company_period_metadata_csv(
        (root / "pilot_power_infrastructure_current.csv").read_text(encoding="utf-8")
    )
    baseline = load_company_period_metadata_csv(
        (root / "pilot_power_infrastructure_baseline.csv").read_text(encoding="utf-8")
    )

    assert len(requests) == 10
    assert {record.company_id for record in current} == {record.company_id for record in baseline}
    assert {(record.ticker, record.quarter) for record in current + baseline} == requests
    assert all(record.published_at.utcoffset() is not None for record in current + baseline)
    assert all(record.published_at_source_url for record in current + baseline)
    assert sum(record.classification.industry == "Electrical Equipment" for record in current) == 4
