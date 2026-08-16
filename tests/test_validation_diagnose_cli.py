from industry_bottleneck_scanner.validation_diagnose_cli import diagnose_result


def test_diagnose_separates_core_and_confirmer_acceleration() -> None:
    payload = {
        "current": {
            "clusters": [
                {
                    "bucket": "Information Technology",
                    "active_metrics": [
                        "backlog_strength",
                        "lead_time_pressure",
                        "pricing_power",
                    ],
                }
            ]
        },
        "baseline": {
            "clusters": [
                {
                    "bucket": "Information Technology",
                    "active_metrics": ["lead_time_pressure"],
                }
            ]
        },
        "acceleration": [
            {
                "bucket": "Information Technology",
                "triggered": True,
                "confirmed": True,
                "watchlisted": False,
                "core_pair_present": True,
                "breadth_change": 0,
                "company_metric_intensity_change": 0.5,
                "metric_prevalence_gain_count": 2,
                "metric_prevalence_gains": ["backlog_strength", "pricing_power"],
                "metric_prevalence_deltas": [
                    {
                        "name": "backlog_strength",
                        "current_companies": 3,
                        "baseline_companies": 1,
                        "change": 2,
                    }
                ],
            }
        ],
    }

    report = diagnose_result(payload)
    cluster = report["clusters"][0]

    assert cluster["any_core_dimension_accelerating"] is True
    assert cluster["both_core_dimensions_accelerating"] is False
    assert cluster["positive_demand_metric_gains"] == ["backlog_strength"]
    assert cluster["positive_scarcity_metric_gains"] == []
    assert cluster["positive_confirmer_metric_gains"] == ["pricing_power"]
    assert cluster["directional_inconsistencies"] == []
    assert cluster["new_active_metrics"] == ["backlog_strength", "pricing_power"]


def test_diagnose_flags_weakening_metric_in_positive_prevalence_gains() -> None:
    payload = {
        "current": {
            "clusters": [
                {
                    "bucket": "Information Technology",
                    "active_metrics": ["backlog_strength", "backlog_weakness", "lead_time_pressure"],
                }
            ]
        },
        "baseline": {"clusters": []},
        "acceleration": [
            {
                "bucket": "Information Technology",
                "triggered": True,
                "confirmed": False,
                "watchlisted": False,
                "core_pair_present": True,
                "breadth_change": 0,
                "company_metric_intensity_change": 0.5,
                "metric_prevalence_gain_count": 3,
                "metric_prevalence_gains": [
                    "backlog_strength",
                    "backlog_weakness",
                    "lead_time_pressure",
                ],
                "metric_prevalence_deltas": [],
            }
        ],
    }

    report = diagnose_result(payload)
    cluster = report["clusters"][0]

    assert cluster["both_core_dimensions_accelerating"] is True
    assert cluster["directional_inconsistencies"] == ["backlog_weakness"]
