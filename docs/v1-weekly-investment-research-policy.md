# V1 weekly investment-research policy

## Objective

The weekly system scans unfamiliar industries broadly, then concentrates GPT
research on the few candidates most likely to produce a 6-18 month public-equity
opportunity. Research quality and source diversity take precedence over token
efficiency in V1. Token feedback is collected so later versions can automate
repetitive work without weakening evidence quality.

## Weekly funnel

1. Code collects, normalizes, deduplicates, and screens the full universe.
2. Every industry receives a compact status row.
3. Rejected industries expose only the failed stage and a 10-180 character
   Korean reason.
4. GPT performs diverse-source discovery, causal interpretation, scenario
   assumption review, and variant-perception review for surviving candidates.
5. Deterministic code computes volume, price, revenue, operating profit, free
   cash flow, and market-expectation comparisons from reviewed assumptions.
6. A Korean report is generated only for a finalist that satisfies evidence,
   scenario, and publication gates.
7. The database stores final reports and compact status rows; it never stores
   prompts, chain-of-thought, research notes, or report drafts.

## V1 source posture

A final report requires at least four source classes and at least two
independent sources. The supported classes are issuer primary material,
customer/supplier/competitor evidence, government or regulatory evidence,
industry or technical evidence, physical-market data, and market expectations.
The GPT research step should actively search for disconfirming and nonstandard
sources rather than merely expanding issuer language.

## Report feedback

Each final report records input, output, and cached input tokens plus useful
claim count, unsupported claim count, unique source count, and duplicate
evidence ratio. Feedback may recommend shorter research packets, denser final
narrative, stronger deduplication, or higher reuse of stable context. These are
optimization recommendations, not permission to remove decision-relevant
evidence.

## Publication invariant

No new information is a valid weekly outcome. If no candidate reaches the
final-report gate, the site publishes status changes and rejection reasons but
does not generate a synthetic report merely to fill a schedule.
