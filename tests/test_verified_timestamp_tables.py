from industry_bottleneck_scanner.validation_advance_cli import VERIFIED_CASES
from industry_bottleneck_scanner.validation_metadata_finalize_cli import _load_verified


def test_all_preselected_labeled_and_control_cases_have_valid_committed_timestamp_tables() -> None:
    expected = {
        "semiconductor-shortage-2021",
        "auto-chip-shortage-2021",
        "semiconductor-2019q2-control",
        "semiconductor-2019q3-control",
        "auto-2019q2-control",
    }
    assert {item.case_id for item in VERIFIED_CASES} == expected

    for item in VERIFIED_CASES:
        assert item.verified.exists(), item.verified
        rows = _load_verified(item.verified)
        assert len(rows) == 8, item.case_id
