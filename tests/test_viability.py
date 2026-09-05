from industry_bottleneck_scanner.aggregation import AccelerationSnapshot
from industry_bottleneck_scanner.viability import assess_phase1_viability


def _snapshot(**overrides) -> AccelerationSnapshot:
    values = dict(
        bucket="Electrical Equipment",
        aggregation_level="industry",
        eligible_companies=4,
        breadth_current=4,
        breadth_baseline=4,
        breadth_change=0,
        breadth_ratio=1.0,
        category_breadth=3,
        metric_breadth=4,
        source_type_breadth=1,
        metric_prevalence_deltas=(),
        metric_prevalence_gains=("backlog_strength",),
        metric_prevalence_gain_count=1,
        category_prevalence_deltas=(),
        category_prevalence_gains=(),
        category_prevalence_gain_count=0,
        new_metrics=(),
        company_metric_intensity_current=2.0,
        company_metric_intensity_baseline=2.0,
        company_metric_intensity_change=0.0,
        qa_share_current=0.4,
        qa_share_baseline=0.3,
        qa_share_change=0.1,
        core_pair_present=True,
        confirmation_count=1,
        confidence_mean=0.8,
        breadth_accelerating=False,
        prevalence_accelerating=False,
        change_reasons=("metric_prevalence_gain",),
        watch_blockers=(),
        watchlisted=False,
        watch_reasons=(),
        triggered=False,
        confirmed=False,
    )
    values.update(overrides)
    return AccelerationSnapshot(**values)


def test_observing_small_pilot_expands_neutral_cohort_without_relaxing_thresholds() -> None:
    decision = assess_phase1_viability((_snapshot(),), eligible_companies=4)

    assert decision.decision == "expand_neutral_cohort"
    assert decision.strongest_stage == "observing"
    assert "do_not_relax_trigger_thresholds" in decision.reason_codes
    assert "pilot_cohort_small" in decision.reason_codes


def test_watchlist_only_still_expands_discovery_sample() -> None:
    decision = assess_phase1_viability(
        (_snapshot(watchlisted=True, watch_reasons=("metric_prevalence_gain",)),),
        eligible_companies=12,
    )

    assert decision.decision == "expand_neutral_cohort"
    assert decision.watchlisted_clusters == 1
    assert "watchlist_only" in decision.reason_codes


def test_triggered_cluster_advances_to_phase2_validation() -> None:
    decision = assess_phase1_viability(
        (_snapshot(triggered=True, watchlisted=False),),
        eligible_companies=20,
    )

    assert decision.decision == "phase2_validation"
    assert decision.triggered_clusters == 1
    assert "triggered_cluster_present" in decision.reason_codes
