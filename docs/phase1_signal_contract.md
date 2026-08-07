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
  "document_id": "source identifier",
  "document_type": "10-K|10-Q|8-K|transcript|release|other",
  "published_at": "ISO-8601 date/time",
  "source_url": "optional",
  "evidence_text": "minimal supporting span",
  "negated": false,
  "resolved": false,
  "extraction_method": "keyword|regex|rule|model",
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

### Subject preservation

Do not collapse `transformers`, `switchgear`, and `cables` into one generic company-level scarcity signal if the text identifies the constrained item. Phase 1 allows `subject=null` until a defensible extractor is implemented.

### Comparison preservation

When the evidence supports it, retain whether the signal is a prior-period change, a guidance/plan revision, a threshold observation, or a forward commitment. Do not invent a comparison when the sentence does not provide one.

## Aggregation

Primary aggregation emphasizes independent issuers and active strengthening evidence.

For each classification bucket and time window record:

- distinct companies with active strengthening signals
- distinct active documents
- scanner-category breadth
- metric breadth
- source/document-type breadth
- strengthening signal count
- weakening/resolution counter-evidence count
- confidence mean
- confidence-weighted active signal count

Repeated phrases from one issuer must not be treated as equivalent to broad confirmation across independent companies.

## Signal acceleration

Phase 1 keeps the trigger components explicit rather than hiding them behind one opaque score.

Components include:

- `breadth_current`: distinct companies with active strengthening evidence
- `breadth_baseline`: comparable baseline breadth
- `breadth_change`: current minus baseline
- `breadth_ratio`: guarded current/baseline ratio
- `category_breadth`: number of Capex/Demand/Scarcity/Pricing categories active
- `metric_breadth`: number of distinct metrics active
- `source_type_breadth`: number of distinct source/document types
- `core_pair_present`: whether both Demand and Scarcity are active
- `confirmation_count`: number of Capex/Pricing confirmation categories active
- `confidence_mean`

## Research trigger hierarchy

### Triggered

Default Phase 1 logic:

```text
minimum independent companies
AND positive breadth acceleration
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
