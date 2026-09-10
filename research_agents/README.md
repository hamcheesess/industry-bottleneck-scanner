# Research agent contracts

Two independent research roles, followed by synthesis/scenarios, adversarial review and a single Korean report writer. Five role definitions do not mean five simultaneous model calls. Reuse source extractions, not unsupported conclusions. Rework only disputed questions. Record input/output tokens and search cost separately; output limits are not total spend limits.

Run the provider-free planner:

```
PYTHONPATH=src python -m industry_bottleneck_scanner.research_agent_plan --config research_agents/roles.json --topic transformers --cutoff 2025-08-29T20:00:00Z --output agent-plan.json
```

This milestone defines roles, budgets, dependencies and telemetry fields. It does NOT execute autonomous research, enforce semantic evidence validation, or publish final reports. Completion records must be accepted by a future validator before dependent execution. Failed or blocked results do not advance. Publication remains disabled.

GitHub workflow expects repository/environment secret OPENAI_API_KEY, based on the user's statement that a key is already registered. Its value is never retrieved or printed. The workflow only checks presence and builds a plan; it does not verify provider authentication or incur model usage. If the registered name differs, change the secret reference. Next integration: model/search adapter, durable evidence and run checkpoints, citation/vintage validation, bounded retries and measured single-agent comparison. Choose model explicitly before paid runs; no silent model default or automatic schedule.
