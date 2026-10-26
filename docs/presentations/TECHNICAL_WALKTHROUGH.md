# Technical walkthrough: reproducible cutoff replay

Proposed length: 6-7 minutes. Audience: engineering and data reviewers. Use the live snapshot for source evidence and the isolated synthetic fixtures for deliberate failure cases. Do not conflate those datasets.

| Time | Evidence or demonstration | Technical point |
| --- | --- | --- |
| 0:00-1:00 | Architecture and CLI | A separate CLI imports fixed Elexon WINDFOR and FUELHH `WIND` endpoints into SQLite. Web GET routes only read a saved snapshot. Migrations and source calls are never triggered by browser requests. |
| 1:00-2:00 | January import evidence and manifest | The live acquisition completed 69 requested windows. The published snapshot `9e2b992d3cb943aa9a82d4c3e71fd68f` has input hash `dfebf7e8895557c162096eb06e3cf1fcf17971e5dbd29974290310de231bb94d`, 744 forecast targets, 1,488 stored actual half-hours and 19,352 scoped semantic observations. Raw hashes, retrieval times and membership stay attached. |
| 2:00-3:00 | Change 15 January cutoff from 09:00 to 09:30 | Selection runs per target with the greatest publication at or before the cutoff. Equal-cutoff publication is eligible; a conflicting newest group is unresolved. The midnight target changes from 7,398 to 7,472 MW, showing why latest-now would leak future revisions. |
| 3:00-4:00 | ADR-002 and accuracy response | The comparator is one exact-start FUELHH half-hour average per hourly WINDFOR target. The adjacent half-hour remains stored. Physical averaging equivalence is unverified; rows carry `temporal_reference_mismatch`. Forecast-minus-reference errors feed pooled MAE/RMSE/bias and daily summaries; no matches yield null metrics. |
| 4:00-5:00 | CSV reconciliation and fixture tests | JSON, CSV, charts and daily rows pin the same snapshot and policy versions. Independent CSV parsing recomputes all matched-row metrics. Deterministic fixtures exercise cutoff equality, revised/conflicting publications, missing reference, zero, month end, failure rollback, and immutable snapshot replay. |
| 5:00-6:00 | Security and browser evidence | Read-only bound SQL, fixed HTTPS source host, bounded retries, strict query validation, local Host/CORS restrictions, safe response headers/CSP, CSV formula handling, black-box Uvicorn probes, browser axe scans and dependency audits are recorded in the security review. The local assignment build has no auth/session or public deployment claim. |
| 6:00-6:45 | Limits and handoff | Source completeness is bounded by requested retrieval windows; later revisions and final settlement state are not guaranteed. A new verified source definition would require a new named policy, tests and snapshot, not relabelling these results. |

## Commands and evidence

Run `make setup`, `make migrate`, `make ingest-fixtures`, `make check`, `make test-browser`, `make test-ui-runtime`, `make benchmark-api`, and `make audit-security` from the project root. The live import and scope audit use `make ingest-january` and `make audit-january` when Elexon is reachable. Review [release validation](../RELEASE_VALIDATION.md), [January evidence](../evidence/elexon-january-import.json), [API benchmark](../evidence/api-benchmark.json), and [comparison policy](../COMPARISON_POLICY.md) alongside the demo.
