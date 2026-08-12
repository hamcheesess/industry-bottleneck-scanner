from industry_bottleneck_scanner.aggregation import AccelerationSnapshot
from industry_bottleneck_scanner.discovery_score import rank_accelerations, score_acceleration


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
        watchlisted=True,
        watch_reasons=("metric_prevalence_gain",),
        triggered=False,
        confirmed=False,
    )
    values.update(overrides)
    return AccelerationSnapshot(**values)


def test_score_is_ranking_aid_and_preserves_explicit_stage() -> None:
    score = score_acceleration(_snapshot())
    assert score.stage == "watchlisted"
    assert 0 < score.score < 100
    assert score.breadth_component == 1.0


def test_confirmed_stage_has_priority_over_triggered() -> None:
    score = score_acceleration(_snapshot(triggered=True, confirmed=True, watchlisted=False))
    assert score.stage == "confirmed"


def test_rank_accelerations_orders_by_score() -> None:
    weak = _snapshot(bucket="Weak", breadth_current=2, confidence_mean=0.65, watchlisted=False)
    strong = _snapshot(bucket="Strong", triggered=True, metric_prevalence_gain_count=3, company_metric_intensity_change=0.75)
    ranked = rank_accelerations((weak, strong))
    assert ranked[0].bucket == "Strong"
