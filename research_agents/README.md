# Research agent contracts

Two independent research roles, followed by synthesis/scenarios, adversarial review and a single Korean report writer. Five role definitions do not mean five simultaneous model calls. Reuse source extractions, not unsupported conclusions. Rework only disputed questions. Record input/output tokens and search cost separately; output limits are not total spend limits.

Run the provider-free planner:

```
PYTHONPATH=src python -m industry_bottleneck_scanner.research_agent_plan --config research_agents/roles.json --topic transformers --cutoff 2025-08-29T20:00:00Z --output agent-plan.json
```

This milestone defines roles, budgets, dependencies and telemetry fields. It does NOT execute autonomous research, enforce semantic evidence validation, or publish final reports. Completion records must be accepted by a future validator before dependent execution. Failed or blocked results do not advance. Publication remains disabled.

GitHub workflow expects repository/environment secret OPENAI_API_KEY, based on the user's statement that a key is already registered. Its value is never retrieved or printed. The workflow only checks presence and builds a plan; it does not verify provider authentication or incur model usage. If the registered name differs, change the secret reference. Next integration: model/search adapter, durable evidence and run checkpoints, citation/vintage validation, bounded retries and measured single-agent comparison. Choose model explicitly before paid runs; no silent model default or automatic schedule.

## Bounded live pilot

`research_agent_runtime` now connects the two research roles to Responses API web search. Explicit model, two requests maximum per fresh output directory, at most four hosted tool calls and 4,000 output tokens per request; these are not dollar/input-token caps. No automatic retries. Model errors and missing credentials are classified without printing provider error bodies. A transport timeout is an uncertain billing outcome and its checkpoint is not automatically retried.

The pilot writes identity, per-role state, original API response, evidence diagnostics and summary. Restoring a selected workflow artifact permits skipping prior calls only when plan/model/prompt identity matches. Changed configuration requires a separate output directory. Full provider usage (including available cached/reasoning details) is retained. Semantic source/date review is mandatory: trace URL presence and model-reported dates do not prove historical availability. Outputs never enter causal registries or the final-report database automatically. Synthesis/review/report roles are still contracts, not live runtime stages.

Reproducible offline validation uses injected responses, including future source rejection, invalid JSON, uncertain transport and duplicate-charge prevention. Actual quality gain and currency cost require the live artifact and a comparable single-agent baseline; no savings claim is made.

API implementation reference: https://developers.openai.com/api/docs/guides/tools-web-search . The first pilot explicitly selects gpt-6-astra; any account/model entitlement failure is retained rather than silently switching models.
