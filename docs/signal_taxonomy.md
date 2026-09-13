# Signal Taxonomy

The scanner starts from industry-independent operating phenomena.  Industry names are aggregation outputs, not the primary search terms.

## Design principles

1. **Change matters more than level.** High capex or large backlog alone is less informative than a revision, acceleration, or broadening across issuers.
2. **Independent issuer breadth matters more than phrase count.** One company repeating `capacity` twenty times is weaker evidence than ten independent companies reporting the same phenomenon.
3. **Direction must be explicit.** `lead times increased` and `lead times declined` cannot enter the same active-scarcity bucket.
4. **Negated/resolved evidence is counter-evidence.** `no longer capacity constrained` must never strengthen the scarcity cluster.
5. **Metrics remain distinct.** Backlog, bookings, book-to-bill, lead time, allocation, sold-out capacity, and qualification barriers are not interchangeable.
6. **Demand + Scarcity is the core research pair.** Capex and Pricing act as confirmation that demand is producing investment response and/or economic capture.
7. **The evidence span remains auditable.** Every AtomicSignal stores the minimal supporting text and matched phrase.

## Capex Scanner

Purpose: identify where investment expectations or physical capacity plans are changing.

| Metric | Strengthening examples | Weakening examples | Why it matters |
| --- | --- | --- | --- |
| `capex_revision_up` | raised capex guidance; capital plan increased | — | expectations are being revised upward |
| `capex_revision_down` | — | lowered capex guidance; reduced capital plan | investment cycle is cooling |
| `capacity_expansion` | adding capacity; new facility; greenfield/brownfield expansion | — | supply response is being initiated |

A high absolute capex number without a revision or concrete expansion action is not sufficient by itself.

## Demand Scanner

Purpose: identify order intake and forward-demand visibility.

| Metric | Strengthening examples | Weakening examples | Notes |
| --- | --- | --- | --- |
| `backlog_strength` | record backlog; backlog grew | — | compare with revenue later when structured financials are available |
| `backlog_weakness` | — | backlog declined; backlog contracted | counter-signal |
| `bookings_strength` | record bookings; strong bookings; record orders | — | order flow before revenue recognition |
| `book_to_bill_above_one` | book-to-bill above 1 | — | threshold signal that orders exceed current billing |
| `forward_capacity_commitment` | reserve capacity; secured capacity; multi-year supply agreement | — | customers are reaching forward to secure future supply |

Future enrichment should extract numeric backlog/revenue and book-to-bill values when explicitly disclosed.

## Scarcity Scanner

Purpose: identify supply elasticity constraints and barriers that prevent supply from responding quickly.

| Metric | Strengthening examples | Interpretation |
| --- | --- | --- |
| `lead_time_pressure` | lead times increased; long lead times | delivery time is stretching |
| `capacity_constraint` | capacity constrained; unable to meet demand | production capacity is binding |
| `supply_tightness` | supply remains tight; limited availability; shortage | broader shortage language |
| `allocation` | product on allocation; supply allocation | supplier is rationing supply |
| `sold_out_capacity` | sold out through 2028; fully booked through | future production is pre-committed |
| `qualification_barrier` | qualification takes X years; customer qualification cycle | new supply cannot enter quickly even if physical capacity exists |

Explicit normalization or negation is counter-evidence and is never counted as active scarcity.

## Pricing Scanner

Purpose: determine whether demand/scarcity is translating into economic capture.

| Metric | Strengthening examples | Weakening examples | Interpretation |
| --- | --- | --- | --- |
| `pricing_power` | pricing remains strong; price increases | — | supplier can hold or raise price |
| `contract_repricing` | repriced contracts; price escalator; take-or-pay | — | economics are embedded in contractual terms |
| `margin_from_pricing` | margin expansion from pricing; price/cost positive | — | price is reaching reported profitability |
| `pricing_weakness` | — | pricing declined; price pressure | scarcity may not be monetizing |

## Comparison basis

Atomic signals expose a coarse `comparison_basis` so downstream analysis can distinguish different evidence types:

- `prior_period`: explicitly increased/decreased versus an earlier period
- `prior_guidance_or_plan`: capex or investment plan revision
- `threshold`: a disclosed threshold such as book-to-bill above 1
- `forward_commitment`: future capacity reservation / sold-out period
- `unspecified`: phrase is relevant but no defensible comparison basis is available

## Trigger hierarchy

A bucket should progress through two levels:

### Research trigger

Default Phase 1 trigger:

```text
minimum independent-company breadth
AND positive breadth acceleration
AND Demand present
AND Scarcity present
AND minimum confidence
```

### Confirmed trigger

A triggered bucket becomes `confirmed` when at least one of the following also appears:

- Capex confirmation: suppliers/customers are increasing investment or adding capacity
- Pricing confirmation: scarcity is converting into price, contract, or margin economics

This is intentionally stricter than keyword frequency alone.

## What Phase 1 does not infer

The deterministic scanner does not yet claim to know:

- the exact constrained product when the sentence is ambiguous
- numerical magnitude unless explicitly extracted by a later structured rule
- whether a company is a customer, supplier, or competitor relative to an emerging bottleneck
- whether the industry cluster is investable
- whether a specific company captures the economics

Those are later research and triangulation stages.
