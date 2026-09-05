# Phase 1 Signal Contract

## Logical scanner categories

The scanner has four logical categories. They are classification dimensions, not necessarily four separate runtime passes.

The detailed metric taxonomy is defined in [`signal_taxonomy.md`](signal_taxonomy.md).

### Capex

Detect changes in expected investment or concrete capacity expansion, not merely high absolute capex.

Primary metrics:

- `capex_revision_up`
- `capex_revision_down`
- `capacity_expansion`

### Demand

Detect order intake and forward-demand strength.

Primary metrics:

- `backlog_strength`
- `backlog_weakness`
- `bookings_strength`
- `book_to_bill_above_one`
- `forward_capacity_commitment`

### Scarcity

Detect inability of supply to satisfy demand or structural barriers to rapid supply response.

Primary metrics:

- `lead_time_pressure`
- `capacity_constraint`
- `supply_tightness`
- `allocation`
- `sold_out_capacity`
- `qualification_barrier`

### Pricing

Detect whether scarcity/demand is translating into economic capture.

Primary metrics:

- `pricing_power`
- `contract_repricing`
- `margin_from_pricing`
- `pricing_weakness`

## AtomicSignal

Every extracted observation is normalized to one atomic record.

Required contract:

```json
{
  "signal_id": "stable-id",
  "scanner": "capex|demand|scarcity|pricing",
  "metric": "taxonomy metric",
  "direction": "strengthening|weakening|stable|unclear",
  "magnitude": "low|medium|high|unknown",
  "company_id": "issuer identifier",
  "ticker": "optional ticker",
  "classification": {
    "sector": "optional",
    "industry": "optional",
    "subindustry": "optional"
  },
  "subject": "what product/capacity/segment the statement refers to, when known",
  "speaker": "optional earnings-call speaker",
  "speaker_title": "optional earnings-call title",
  "source_section": "prepared|qa|optional other section",
  "document_id": "source identifier",
  "document_type": "10-K|10-Q|8-K|earnings_call_turn|release|other",
  "published_at": "ISO-8601 date/time",
  "source_url": "optional",
  "evidence_text": "minimal supporting span",
  "negated": false,
  "resolved": false,
  "extraction_method": "keyword|regex|semantic_local|review_accept|other auditable method",
  "confidence": 0.0,
  "matched_phrase": "exact deterministic phrase when applicable",
  "comparison_basis": "prior_period|prior_guidance_or_plan|threshold|forward_commitment|unspecified"
}
```

## Important semantic rules

### Negation

Statements such as `we are no longer capacity constrained` must not be counted as active scarcity.

### Direction

Strengthening and weakening observations remain distinct. An explicit weakening taxonomy pattern such as `pricing declined` is not automatically labeled as a resolved historical constraint.

### Resolution

A strengthening constraint phrase followed by explicit normalization can be marked `resolved=true`. Resolved signals remain available as counter-evidence but do not contribute to active opportunity breadth.

### Subject and speaker provenance

`subject` is the constrained product/capacity/segment when known. Earnings-call speaker identity is separately preserved as `speaker` and `speaker_title`; it must not be substituted for the economic subject.

### Comparison preservation

When the evidence supports it, retain whether the signal is a prior-period change, a guidance/plan revision, a threshold observation, or a forward commitment. Do not invent a comparison when the sentence does not provide one.

## Aggregation

Primary aggregation emphasizes independent issuers and active strengthening evidence.

For each classification bucket and time window record:

- distinct companies with active strengthening signals
- distinct active documents
- scanner-category breadth
- metric breadth
- per-category distinct-company prevalence
- per-metric distinct-company prevalence
- unique company-metric pairs
- unique company-category pairs
- source/document-type breadth
- prepared-vs-Q&A evidence counts and Q&A share
- strengthening signal count
- weakening/resolution counter-evidence count
- confidence mean
- confidence-weighted active signal count

Repeated phrases from one issuer must not be treated as equivalent to broad confirmation across independent companies.

## Signal acceleration

Phase 1 keeps trigger components explicit rather than hiding them behind one opaque score.

Two forms of acceleration are tracked.

### 1. Breadth acceleration

A phenomenon spreads to additional independent companies in the current window:

```text
breadth_current > breadth_baseline
```

### 2. Prevalence acceleration

Matched-cohort breadth may saturate, especially in small pilots. A phenomenon can still accelerate when multiple metrics spread to more companies and the number of unique company-metric incidences rises.

Default prevalence evidence requires both:

```text
at least 2 metrics with higher distinct-company prevalence
AND company-metric incidence per eligible company rises by at least 0.25
```

Raw mention count is deliberately excluded from the trigger. Repeating the same phrase several times in one transcript must not manufacture acceleration.

Additional auditable fields include:

- `metric_prevalence_gains`
- `category_prevalence_gains`
- `new_metrics`
- `company_metric_intensity_current`
- `company_metric_intensity_baseline`
- `company_metric_intensity_change`
- `qa_share_current`
- `qa_share_baseline`
- `qa_share_change`
- `breadth_accelerating`
- `prevalence_accelerating`

Q&A-share change is diagnostic context, not by itself a trigger.

## Research trigger hierarchy

### Triggered

Default Phase 1 logic:

```text
minimum independent companies
AND (breadth acceleration OR prevalence acceleration)
AND Demand + Scarcity core pair
AND minimum category breadth
AND minimum confidence
```

### Confirmed

A triggered cluster becomes confirmed when at least one configurable confirmation category is present. The default confirmation set is:

- Capex
- Pricing

This produces a useful hierarchy:

```text
Demand + Scarcity acceleration
    -> research trigger
    -> Capex and/or Pricing confirmation
    -> stronger research candidate
```

Phase 1 must emit the evidence and every trigger component so a human can inspect why a cluster fired.
