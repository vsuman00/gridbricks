# Backend test report

Date: 26 October 2026. Scope: the local FastAPI service, analytical rules, SQLite snapshot reads, offline fixture import, CSV export, security controls, and saved January 2026 data. No source download or new live import was performed.

## Result

**Functional checks passed in the tested scope.** Ruff lint and format checks passed, and all 151 backend tests passed. A separate Ruff security-rule scan passed. `uv audit` found no known vulnerabilities or adverse project statuses in the 33 selected packages. The saved live snapshot returned 744 expected and 744 matched January intervals. No new analytical or HTTP defect was reproduced.

The initial audit found one **PARTIAL** operational gap: [the architecture](ARCHITECTURE.md#9-local-operation-security-and-diagnostics) required structured request and import logs. The follow-up below closes that gap in the tested local scope.

## Fresh verification

| Check | Result |
| --- | --- |
| `make check-backend` | Ruff lint and format passed; 151 unit and integration tests passed in 7.71 seconds. |
| `ruff check --select S` | Passed on backend source. |
| `uv audit --project backend --locked --python-version 3.12` | No known vulnerabilities or adverse statuses in 33 selected packages. Advisory results can change. |
| `make audit-january` | Read the saved live snapshot `9e2b992d3cb943aa9a82d4c3e71fd68f`: 744 expected, 744 selected forecasts, 744 complete exact-time actual references, and 744 matched. |
| Fresh offline fixture import and January audit in a temporary directory | Completed without a live source request. The designed 744-row grid had 742 selected forecasts and 741 matches: one forecast conflict, one missing forecast, and one missing exact-time actual. |
| Live loopback HTTP probes | The 15 January decision's first target selected 7,398 MW at 09:00 and 7,472 MW at 09:30. Decision JSON had 24 rows and no actual or metric fields. Full-month Accuracy had 744 rows and 744 matches. Invalid date, unknown snapshot, and POST returned 422, 404, and 405. The eligible-revisions response contained no publication after the cutoff. The active snapshot ID was unchanged after the probes. |
| [Independent CSV reconciliation](evidence/backend-test-reconciliation-2026-10-26.json) | An owned local API served a 744-row Accuracy export and 24-row Decision export. JSON/CSV metadata, row values, source and actual lineage, and recomputed metrics agreed. |
| [Full-January API benchmark](evidence/backend-test-benchmark-2026-10-26.json) | Five warmups and 100 sequential pinned HTTP requests, 744 rows each: p50 128.91 ms, p95 138.06 ms, maximum 150.21 ms. The documented local p95 target is 1,000 ms. |

## Coverage and limits

The automated suite exercises cutoff equality and revision conflicts, missing and zero values, exact-time actual selection, pooled equations, date bounds, snapshot membership and rollback, failed source windows, CSV formula handling, and real-server security responses. The black-box suite uses an owned Uvicorn process; the fresh live probes used the already running local backend. The benchmark and reconciliation each started their own local process and read the saved snapshot.

The live result confirms behavior for the stored source windows, not a fresh Elexon acquisition or exhaustive historical revision coverage. WINDFOR's physical averaging interval remains unverified; Accuracy uses the documented timestamp-matched half-hour reference. The timing result is a local sequential measurement on the recorded host, not a concurrency or production-service guarantee. The vulnerability scan covers published advisories for the selected dependency graph; it does not prove supply-chain safety. No public hosting, authentication, or multi-user load test was performed.

## Structured logging follow-up: VERIFIED

The API now emits one JSON-line `http_request` event per request to stderr, with a generated request ID also returned in `X-Request-ID`. Events include the allowlisted route and method, status, duration, safe error code, resolved snapshot, and validated decision bounds and cutoff when available. Raw URLs, query strings, and response bodies are excluded. The import CLI emits start, per-window start/finish/failure, publication, and overall failure events. Window events include dataset, bounds, attempt count, record/defect counts, and duration; publication includes the snapshot and manifest hash. Failed retrievals have a distinct event and code from missing source observations.

`make check-backend` passed Ruff lint/format and 155 tests in 7.61 seconds after the final failed-window bound check. A separate Ruff security-rule scan passed. An owned offline CLI process emitted 140 import events, including 69 completed windows; an owned Uvicorn process emitted request events whose IDs matched response headers. The isolated Chromium suite passed 20 cases. A [post-change benchmark](evidence/backend-logging-benchmark-2026-10-26.json) of 100 warm, sequential full-January requests measured 133.15 ms p95 against the 1,000 ms local target. This follow-up did not download new Elexon data or test public hosting.

Frontend integration was checked again after the logging change: `make check-frontend` passed lint, types, 79 tests and the production build. The isolated 20-case Chromium suite passed against a synthetic snapshot served by the real API. A separate owned production-preview browser run read the saved live January snapshot: data-status, forecast and accuracy all returned 200 with `X-Request-ID`; Decision and Accuracy rendered, with no browser page errors. This confirms the read-only frontend/API path for the saved snapshot, not a fresh source import.
