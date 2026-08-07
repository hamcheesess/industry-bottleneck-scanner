# Recall strategy for transcript discovery

## Objective

Phase 1 is a discovery system. Missing a genuinely emerging operating signal can be more damaging than admitting a manageable number of false-positive candidates. Retrieval therefore favors recall first, followed by stricter signal classification and cross-company confirmation.

## Retrieval layers

The scanner should evolve through three local-first layers:

1. Exact phrases — highest auditability and precision.
2. Flexible regex patterns — word-order, inflection, and short-gap variation without an LLM.
3. Local semantic retrieval — later, for paraphrases that do not share enough lexical surface form.

A raw transcript must never be sent wholesale to an LLM by default.

## Current implementation

Exact phrase and regex matching are active. Examples that should map to the same concept include:

- `record backlog`
- `backlog reached a record level`
- `backlog increased materially`

and:

- `capacity constrained`
- `customer demand exceeded available capacity`
- `requirements outpaced available output`

Regex matches preserve the actual matched text in `AtomicSignal.matched_phrase` and record `extraction_method=regex`.

## Transcript handling

One earnings call is split into turn-level `SourceDocument` records before scanning. Speaker and title provenance are preserved. This avoids treating a 20,000-word call as one opaque document and allows later weighting of management statements versus analyst questions.

The actual call publication/event timestamp is required from metadata. The fiscal quarter must not be used as a fabricated publication date because acceleration analysis depends on real chronology.

## Precision controls after retrieval

Candidate signals are then filtered by:

- explicit strengthening vs weakening direction
- negation and resolution markers
- independent-company breadth
- metric/category breadth
- Demand + Scarcity core-pair requirement
- Capex/Pricing confirmation

This design intentionally separates high-recall retrieval from stricter cluster confirmation.

## Next step

Add a provider-independent semantic retriever that runs locally on candidate transcript passages. Semantic-only hits should enter a lower-confidence review tier until repeated cross-company evidence validates the expression.
