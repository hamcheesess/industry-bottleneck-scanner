from pathlib import Path

from industry_bottleneck_scanner.validation_collection_cli import DEFAULT_REQUEST_FILES


def test_validation_collection_plan_includes_retained_power_pilot() -> None:
    assert Path("experiments/pilot_power_infrastructure_requests.csv") in DEFAULT_REQUEST_FILES
    assert Path("experiments/validation_semiconductor_2019q3_control_requests.csv") in DEFAULT_REQUEST_FILES
    assert Path("experiments/validation_auto_2019q2_control_requests.csv") in DEFAULT_REQUEST_FILES
