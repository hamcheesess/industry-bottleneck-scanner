# Research charter — 2026-09-12

Status: agreed objectives, flexible report requirements, discovery entry points and staged research stopping policy. This is a policy record, not a claim that production code already enforces it.

## Purpose agreed with the user

Build analytical advantage from public information: broad discovery, deep investigation, causal explanation, company comparison, counter-hypotheses, and transparent prospective cash-flow scenarios. Help an initially unfamiliar reader understand customers, technologies, products, business models, competition, reinvestment and valuation. Report volume, source count, agent agreement and confident prose are not evidence of advantage.

Produce a satisfactory Korean PDF benchmark FIRST, then codify repeatable quality. API automation remains parked. Preserve the 6–18 month prospective investment horizon and both axes: existing beneficiaries versus priced expectations, and downstream value-chain opportunities. Bottlenecks are one mechanism, not a mandatory condition for investment merit. Do not fix chapter count, titles or order. Select a coherent narrative for each industry/company; enforce analytical coverage and reader comprehension instead. This supersedes earlier fixed-nine-chapter instructions and historical report-contract templates for future reports.

## Required report improvements from the attached feedback

1. Explain the customer's problem, product function, technical vocabulary, substitutes, representative firms and purchasing economics before discussing valuation.
2. Trace each selected value-chain edge: change → customer requirement → purchase → supplier exposure → profit capture → reinvestment → cash. Investigate actual beneficiary companies rather than stop at route ranking.
3. Explain each company's products, buyers, selling model, competition and cost structure before numerical scenarios.
4. Show how evidence supports scenario drivers; distinguish segment-level evidence from aggregate company assumptions. Do not claim product FCF decomposition when none was performed.
5. Label sources in prose with institution, date, relevant content and readable links; identifiers remain for traceability, not as the only explanation.
6. Distinguish not yet researched, searched but not found, inaccessible/nonpublic, and conflicting. A material unresearched question triggers more research before finalization. Never turn lack of retrieval into proof of absence.
7. Explain the leading hypothesis, alternatives, strongest counterevidence, and what would change the conclusion. Research priority is not purchase approval.
8. Business connections require evidence of customer reuse, cost reduction, switching difficulty or incremental returns; a diverse product portfolio alone is not a moat.

## Evidence Research Protocol — adopted controls

The user supplied a final protocol in this conversation. This section is an operational digest, not a verbatim replacement of its full schema.

- Separate source authority (tier_1a official; tier_1b verified direct professional reporting; tier_2 independent specialist; tier_3 stakeholder/field communication; tier_4 exploratory secondary) from directness (original document, direct reporting/interview, derived analysis, summary, unknown).
- Classify the claim, not merely the publisher. Management forecasts in an official filing remain forecasts; independent reporting of an anonymous claim remains reported. Lower tiers are useful for discovery, not automatically excluded.
- Keep actual, committed_future, reported, forecast, opinion and inference separate. Future commitments require binding/conditional/cancelable/non_binding/unknown strength and relevant conditions.
- Validate entity, metric, unit, currency, period, geography, consolidated/segment scope and the whole claim against the citation. Direct/derived/inferred/partial/unsupported relationships must remain explicit.
- Derived claims require original atomic IDs, formula and assumptions. Inferences require premises, alternatives and limits. Split partial claims; remove unsupported factual assertions from conclusions, scores and valuation premises.
- Preserve verification states: verified, partially_verified, not_found, not_public, access_limited, conflicting, not_applicable, negative_confirmed. Explicit authoritative negative statements plus scope and period are necessary for negative confirmation. Do not average conflicting sources.
- Track independence_group; repeated coverage of one original disclosure is one evidential origin. Pursue corrections and distinguish later corrections from what was knowable at a historical cutoff.
- Record source publication/availability time, retrieved_at, valid_as_of, freshness_class, stale_after. Retrieval today does not imply historical availability. Current freshness expiry does not erase a valid historical observation. Unknown availability limits admissibility.
- Core claims/calculations must trace to atomic fact IDs. Hypotheses record stage, highest confirmed stage, materiality, confidence, confirmation metrics, falsification conditions and affected financial variables.
- No mandatory source-class count. Seek materially different classes where available; record structural absence rather than fill quotas. This supersedes the older prose requirement of four classes/two sources in docs/v1-weekly-investment-research-policy.md; production gate migration remains to be audited and implemented separately.
- Analyst scenario assumptions are not invented Actuals: keep a separate assumption record with rationale, range, sensitivity and supporting fact IDs. The user's protocol has calculation_assumptions but no standalone assumption type; a future schema extension should preserve this distinction, not silently relabel assumptions as verified facts.
- Source authority is not a mechanical confidence score. Claim relevance, incentives, directness and conflicting evidence matter. This protocol reduces false positives; it does not establish investment truth by itself.

## Implementation sequence

1. Use the agreed discovery entry points and apply the staged research stopping policy below.
2. Build question-led research packets for demand, competition/value chain, and company economics; use a synthesis/critical review role. Agents return evidence records and concise findings, not repeated full reports.
3. Direct more research to uncertain questions that could change candidate selection or cash-flow assumptions.
4. Produce an industry tutorial and business-model explanations, then evidence-linked scenarios, reverse valuation and prospective catalysts/falsifiers.
5. Validate dates, citations, arithmetic and readable Korean PDF; obtain substantive user feedback before API automation.
6. Codify stable steps: data normalization, provenance, deduplication, calculations, change tracking and publishing. Do not claim semantic truth from schema validation alone.
7. Publish final reports only; retain short dated stage/reason records for deferred/rejected industries. Keep reusable evidence separate from the reader-facing final-report database.

## Discovery expansion accepted

Retain broad relative-price/breadth signals as one entry; supplement with operating-change discovery (orders, inventory, pricing, utilization, customer budgets), structural change (technology, regulation, substitution), and propagation from researched industries. A market trigger is a research lead, not a universal prerequisite or a buy signal. Short preliminary reconnaissance selects where deeper investigation has decision value. No new weights, thresholds or historical trigger dates are changed by this policy record.

## Historical benchmark guard

AI networking case remains 2025-06-30T20:00:00Z until explicitly changed. Later examples supplied for writing feedback are not admissible historical evidence. Distinguish first stored monthly pass from daily first anomaly and retrospective user-selected cases from outcome-blind discovery.

## Flexible narrative, consistent analytical quality

The reader must understand the change and selection rationale, customer problem, technology/products, business model, competition/moat, actual purchase evidence, relevant value-chain opportunities, reinvestment/cash conversion, valuation versus market expectations, prospective 6–18 month opportunity, counter-hypotheses and limitations. These are coverage requirements, not mandatory separate chapters. Combine, reorder or deepen them to fit the company; explain non-applicability rather than insert filler. Include an actual report-specific table of contents and readable source references. Judge continuity from customer problem to economics to valuation, not heading compliance.

The two analytical axes are qualitative economic understanding and quantitative scenario/expectation valuation. Preserve the two opportunity routes (existing beneficiaries and downstream beneficiaries) without confusing them with the analytical axes. DCF estimates intrinsic value; reverse valuation diagnoses expectations; separate horizon price scenarios explain earnings/cash changes versus multiple changes. Model selection follows economics, not whichever yields the highest price.

## Hard investment horizon

The user's professional/proprietary-trading objective requires a credible observable earnings/cash-flow improvement or market-expectation revision within 6–18 months. Long-run promise without a supported near-term realization path is horizon-ineligible, not a bad company. Record milestones, timing evidence, delay risks and falsifiers. Do not require unavailable future actuals and do not promise share-price realization.

## Staged research stopping policy

Purpose: avoid spending deep-research resources on low-value leads without mistaking missing evidence for disproof. Apply incrementally to every discovery route. Never require a full DCF before a preliminary decision.

1. Intake: establish source/time/entity and what actually changed. Deduplicate and reuse prior work. Archive duplicates; mark post-cutoff evidence inadmissible for that replay. One failed market trigger does not veto the operating/technology/value-chain routes.
2. Preliminary economic relevance: seek a plausible material link from change to customer spending or supplier economics. Stop this route if evidence contradicts the proposed link or its effect is immaterial; defer if not yet assessable. Weak exploratory sources may generate verification leads but cannot support final investment approval.
3. Horizon and investigability: assess credible 6–18 month milestones and accessible evidence routes. Mark horizon mismatch separately from access_limited/not_public/not_found. A material unknown can justify deeper investigation where a promising route exists; it does not mandate unlimited search.
4. Targeted deepening: investigate the few uncertainties that could change selection or financial assumptions. At each research batch, note the question, new evidence and next useful source/action. Pause when results only repeat known material and no productive next route is identified; label research exhaustion/deferred, not negative_confirmed. No arbitrary token ceiling is a substitute for evidence adequacy. Additional effort remains justified for material, resolvable uncertainties.
5. Company and valuation screening: assess profit capture, reinvestment and preliminary price expectations. Deprioritize value-insufficient candidates only with disclosed assumptions; otherwise defer valuation. Preserve viable downstream branches rather than rejecting the whole industry because one company fails.
6. Full report: proceed only for candidates with sufficient substantive investigation to present connected analysis. Report completion and investment eligibility are separate. A completed investigation may conclude no attractive trade; do not manufacture one.

Record each decision compactly: candidate_id, entity_scope, discovery_route, information_cutoff, assessed_at, stopped_stage, decision (continue/defer/reject_route/reject_candidate/archive_duplicate), reason_code, short Korean reason, evidence_fact_ids, search_status, searched_scope, unresolved_question, resume_condition and next_review_or_event. Use null with explanation for unavailable evidence IDs; never fabricate them. Keep investment rejection distinct from an evidence verification status.

Illustrative reason codes: duplicate, economically_immaterial, mechanism_contradicted, horizon_mismatch, evidence_access_limited, evidence_not_found, conflicting_evidence, research_yield_exhausted, profit_capture_weak, valuation_insufficient. They are labels, not automatic factual judgments or calibrated thresholds.

Reader-facing status example (illustrative, not an actual industry conclusion): “기술 변화 경로 / 시간 적합성 단계에서 보류: 확인된 상용화 일정이 투자 기간 밖에 있음. 양산 일정 단축 또는 기간 내 유상 계약 확인 시 재검토.” Display stage, dated reason and material reopening condition; do not generate a full rejected-sector report.

Reuse source records across candidates and routes; investigate only new or changed material where appropriate. Review deferred candidates when reopening evidence appears rather than repeating identical searches every week. Production enforcement, schema migration and calibrated budgets remain implementation work; this update records the operative research instructions only.
