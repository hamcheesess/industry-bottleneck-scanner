# Recall strategy for transcript discovery

## Objective

Phase 1 is a discovery system. Missing a genuinely emerging operating signal can be more damaging than admitting a manageable number of false-positive retrieval candidates. Retrieval therefore favors recall first, followed by stricter adjudication and cross-company confirmation.

## Local retrieval stack

The implemented stack is:

1. exact phrases — highest auditability and precision
2. flexible regex patterns — word-order, inflection, and short-gap variation
3. optional local semantic retrieval — paraphrases with little lexical overlap

A raw transcript is never sent wholesale to an LLM by default.

Examples that should map to the same concept include:

- `record backlog`
- `backlog reached a record level`
- `backlog increased materially`

and:

- `capacity constrained`
- `customer demand exceeded available capacity`
- `requirements outpaced available output`

Regex hits preserve their actual matched span. Lexical and semantic hits on the same evidence/metric are merged before adjudication.

## Transcript handling

Each earnings call is split into turn-level `SourceDocument` records before retrieval. Speaker/title provenance and prepared-vs-Q&A section labels are preserved separately from the economic `subject` field.

The actual call/event timestamp comes from explicit metadata. Fiscal quarters are never fabricated into event dates.

## Semantic-only review tier

Local semantic retrieval is deliberately not equivalent to an accepted signal. Medium-confidence semantic-only candidates are persisted to a review queue and excluded from aggregation until resolved.

A high-confidence semantic candidate may pass deterministic adjudication, but the default design remains conservative: semantic retrieval expands recall; it does not redefine the taxonomy on its own.

## Repeated novel management language

Pending semantic-only candidates are also a source of vocabulary discovery. The system can cluster similar expressions **within the same scanner/metric** and require repeated evidence across independent issuers.

```text
semantic-only review candidates
  -> local embedding clusters
  -> independent-company breadth threshold
  -> novel-language candidate
  -> human/research review
  -> optional future vocabulary update
```

Novel-language clusters are never auto-promoted into `AtomicSignal` records and never mutate production vocabulary automatically. This keeps the scanner capable of learning new management language without turning an embedding coincidence into a research signal.

## Precision controls after retrieval

Accepted signals and cluster triggers remain constrained by:

- strengthening vs weakening direction
- negation and resolution markers
- independent-company breadth
- comparable current/baseline issuer cohorts
- explicit industry-level aggregation by default
- metric/category breadth
- Demand + Scarcity core-pair requirement
- Capex/Pricing confirmation
- signal-quality diagnostics such as issuer concentration and classification completeness

This preserves a clear separation between high-recall retrieval and stricter research-trigger confirmation.
