from __future__ import annotations

from dataclasses import dataclass

from .aggregation import AccelerationSnapshot
from .discovery_score import DiscoveryScore, rank_accelerations


@dataclass(frozen=True)
class Phase1ViabilityDecision:
    decision: str
    strongest_bucket: str | None
    strongest_stage: str | None
    strongest_score: float | None
    eligible_companies: int
    watchlisted_clusters: int
    triggered_clusters: int
    confirmed_clusters: int
    reason_codes: tuple[str, ...]


def assess_phase1_viability(
    acceleration: tuple[AccelerationSnapshot, ...],
    *,
    eligible_companies: int,
) -> Phase1ViabilityDecision:
    """Choose the next research gate without weakening discovery thresholds.

    Phase 2 is validation, so a real triggered cluster is enough to justify moving a
    cluster into validation. If the bounded pilot only produces observing/watchlisted
    evidence, the correct next step is a broader industry-neutral discovery cohort rather
    than lowering thresholds or treating weak evidence as a bottleneck.
    """

    if eligible_companies < 0:
        raise ValueError("eligible_companies must be non-negative")

    scores: tuple[DiscoveryScore, ...] = rank_accelerations(acceleration)
    strongest = scores[0] if scores else None
    watchlisted = sum(item.watchlisted for item in acceleration)
    triggered = sum(item.triggered for item in acceleration)
    confirmed = sum(item.confirmed for item in acceleration)

    reasons: list[str] = []
    if confirmed:
        decision = "phase2_validation"
        reasons.append("confirmed_cluster_present")
    elif triggered:
        decision = "phase2_validation"
        reasons.append("triggered_cluster_present")
    else:
        decision = "expand_neutral_cohort"
        if watchlisted:
            reasons.append("watchlist_only")
        else:
            reasons.append("no_watch_or_trigger")
        reasons.append("do_not_relax_trigger_thresholds")

    if eligible_companies < 10:
        reasons.append("pilot_cohort_small")

    return Phase1ViabilityDecision(
        decision=decision,
        strongest_bucket=strongest.bucket if strongest else None,
        strongest_stage=strongest.stage if strongest else None,
        strongest_score=strongest.score if strongest else None,
        eligible_companies=eligible_companies,
        watchlisted_clusters=watchlisted,
        triggered_clusters=triggered,
        confirmed_clusters=confirmed,
        reason_codes=tuple(reasons),
    )
