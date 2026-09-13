from __future__ import annotations

from dataclasses import dataclass

from .aggregation import AccelerationSnapshot


@dataclass(frozen=True)
class DiscoveryScore:
    bucket: str
    score: float
    stage: str
    breadth_component: float
    prevalence_component: float
    intensity_component: float
    confirmation_component: float
    evidence_component: float
    qa_component: float


def score_acceleration(snapshot: AccelerationSnapshot) -> DiscoveryScore:
    """Convert auditable acceleration components into a bounded discovery score.

    The score is a ranking aid, not an alternative trigger. Existing watch/trigger/confirm
    booleans remain the production gates. This prevents a weighted score from silently
    weakening the explicit Demand+Scarcity and independent-company requirements.
    """

    eligible = max(snapshot.eligible_companies, 1)
    breadth_component = min(1.0, snapshot.breadth_current / eligible)
    prevalence_component = min(1.0, snapshot.metric_prevalence_gain_count / 3.0)
    intensity_component = min(1.0, max(0.0, snapshot.company_metric_intensity_change) / 0.75)
    confirmation_component = min(1.0, snapshot.confirmation_count / 2.0)
    evidence_component = min(1.0, max(0.0, snapshot.confidence_mean))
    qa_component = min(1.0, max(0.0, snapshot.qa_share_current))

    score = 100.0 * (
        0.25 * breadth_component
        + 0.20 * prevalence_component
        + 0.15 * intensity_component
        + 0.15 * confirmation_component
        + 0.20 * evidence_component
        + 0.05 * qa_component
    )

    if snapshot.confirmed:
        stage = "confirmed"
    elif snapshot.triggered:
        stage = "triggered"
    elif snapshot.watchlisted:
        stage = "watchlisted"
    else:
        stage = "observing"

    return DiscoveryScore(
        bucket=snapshot.bucket,
        score=round(score, 2),
        stage=stage,
        breadth_component=round(breadth_component, 4),
        prevalence_component=round(prevalence_component, 4),
        intensity_component=round(intensity_component, 4),
        confirmation_component=round(confirmation_component, 4),
        evidence_component=round(evidence_component, 4),
        qa_component=round(qa_component, 4),
    )


def rank_accelerations(items: tuple[AccelerationSnapshot, ...]) -> tuple[DiscoveryScore, ...]:
    return tuple(
        sorted(
            (score_acceleration(item) for item in items),
            key=lambda item: (-item.score, item.bucket),
        )
    )
