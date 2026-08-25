# Source-agnostic operating evidence

Status: **active Phase-2 contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

## Boundary

Every issuer-language provider terminates at the same normalization boundary:

```text
SEC EDGAR / company IR / optional transcript
  -> PublicDisclosure
  -> section-level SourceDocument
  -> existing deterministic scanner
  -> AtomicSignal
  -> OperatingSupport
  -> Causal Diagnosis
```

Provider clients never appear in causal, state, convergence, or ranking modules. Raw source
documents are cached independently; normalized artifacts preserve provider, source URL,
publication/retrieval timestamps, stable document identity, and a content fingerprint.

## Implemented contracts

- `disclosure_documents.py` normalizes releases, presentations, SEC filings, and
  customer/supplier/competitor disclosures to the existing `SourceDocument` contract.
- `source_scan.py` runs the existing scanner across arbitrary eligible documents and retains
  analyst-question exclusion for structured transcript turns.
- `operating_support.py` separates future, stale, pre-existing, recent-update, and trigger-era
  evidence. Missing sources are coverage gaps, never negative evidence.
- `causal_diagnosis.py` accepts provider-independent `OperatingSupport`; the legacy
  `AccelerationSnapshot` path remains compatible and optional.
- `operating_evidence_cli.py` writes a source manifest, `AtomicSignal` JSONL, and the versioned
  `operating-support-v1` artifact.

## SEC EDGAR adapter

`sec_edgar.py` uses the public, unauthenticated SEC submissions and filing archive endpoints.
It collects trigger-scoped 8-K, 10-Q, and 10-K primary documents and discovers `EX-99.*`
attachments to 8-K filings, including common earnings-release exhibits.

Safety and replay rules:

- require a declared organization/contact `SEC_USER_AGENT`;
- pace requests at 0.2 seconds by default, below the SEC maximum of 10 requests/second;
- accept only `data.sec.gov` and `www.sec.gov` HTTPS URLs;
- cache validated raw responses before normalization;
- load overlapping supplemental submission-history files when the requested period is older
  than the recent submissions window;
- reject filings accepted after the exact timezone-aware `as_of` timestamp;
- skip unsupported binary attachments explicitly instead of pretending they were scanned;
- fail when an issuer safety budget would be exceeded rather than silently truncating the
  company set.

SEC EDGAR does not require an API key. `SEC_USER_AGENT` is a fair-access identity, not a secret
token, but it should be configured outside command history when it contains a personal contact.

Example trigger-scoped collection:

```bash
export SEC_USER_AGENT="Research Project contact@example.com"

ibs-sec-disclosures \
  --companies-csv artifacts/trigger-companies.csv \
  --since 2024-11-01 \
  --as-of 2026-08-21T23:59:59+00:00 \
  --cache-dir var/cache/sec-edgar \
  --output-jsonl artifacts/operating/disclosures.jsonl \
  --diagnostics artifacts/operating/sec-collection.json
```

The company CSV requires `cik` plus `company_id` or `issuer_id`. Optional `ticker`, `sector`,
`industry`/`bucket`, and `subindustry` fields preserve the Market Trigger classification join.

The production bootstrap processes the frozen research queue sequentially in issuer batches of
at most 100 at four requests per second. Each batch persists normalized disclosures and raw
cache checkpoints. Failures also persist a `sec-edgar-collection-v1` diagnostic classified as
`configuration`, `sec_access_policy`, `sec_rate_limit`, `sec_transport`,
`sec_response_contract`, or `sec_collection_error`; a failed batch is never reported as an
empty-evidence result. Raw cache artifacts can be supplied to the workflow as an explicit
failed-run checkpoint, so transient transport timeouts resume without refetching validated SEC
responses.

Scan the resulting provider-neutral disclosure artifact:

```bash
ibs-operating-evidence \
  --disclosures-jsonl artifacts/operating/disclosures.jsonl \
  --expected-companies-csv artifacts/trigger-companies.csv \
  --bucket "SIC 3612 — Power, Distribution, and Specialty Transformers" \
  --as-of 2026-08-21T23:59:59+00:00 \
  --output-dir artifacts/operating
```

## Remaining Phase-2 source work

SEC is the first executable adapter. Investor presentations and company-IR releases that are
not filed as SEC exhibits can already enter through `PublicDisclosure` JSONL, but automated
IR-site discovery remains source-specific future work. Transcript providers stay optional.
