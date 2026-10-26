# Local assignment release validation

Date: 26 October 2026. Scope: the implemented React/SCSS and FastAPI application, saved Elexon January snapshot, offline synthetic fixtures, and local security/performance checks. The interactive mockup preview was removed after the user requested a real-only frontend. This record supports a local assignment demonstration. It is not a public deployment or a guarantee that every defect has been found.

## Requirement and evidence map

| Requirement or task | Implemented result | Evidence |
| --- | --- | --- |
| T01 source and comparison contract | Fixed WINDFOR/FUELHH `WIND` scope, recorded bounds and source ambiguity; named exact-time half-hour reference benchmark | [Research](COMPARISON_POLICY.md), [ADR-002](decisions/0002-timestamp-matched-reference.md), [primary-source samples](evidence/t01-comparison-research.json) |
| T02-T03 setup, ingestion and snapshots | Locked setup, SQLite migration, separate CLI, raw hashes/lineage, immutable membership, atomic active pointer and resumable windows | `make setup`, `make migrate`, fixture/live imports, 151 backend tests, [live acquisition](evidence/elexon-january-import.json) |
| T04-T05 historical Decision | Per-target latest eligible publication, cutoff equality, conflicts/gaps, provenance, responsive UI, no future actuals | API/unit tests, 15 stored-data browser cases, [live Decision screenshots](evidence/ui/live-decision-1440.png) |
| T06-T07, T09 retrospective Accuracy | One exact-time half-hour actual reference per hourly target, conservative actual revisions, pooled metrics, daily summaries, chart and table | Alignment/metric/API tests, [live Accuracy screenshots](evidence/ui/live-accuracy-1440.png), [ADR-002](decisions/0002-timestamp-matched-reference.md) |
| T08 January coverage | All 69 requested live windows succeeded; audit covers all January decisions even when an active snapshot is narrower | [January evidence](evidence/elexon-january-import.json), month-backfill and partial-snapshot audit regression |
| T10 CSV | Full grid, pinned snapshot/policies, missing reasons, source and constituent provenance; formula-safe text | Export tests, browser download, [independent live CSV reconciliation](evidence/live-export-reconciliation.json) |
| T11 failures and interaction | Offline fixtures, source/API/no-data distinction, stale response guards, unknown snapshot recovery, keyboard and responsive views | 78 frontend tests, 19 Chromium cases, nine axe scans, [browser report](BROWSER_TEST_REPORT.md) |
| T12 packaging | Run instructions, source identity, audit, API/browser timing, scoped security review, and two 5-7 minute outlines | This record, [client](presentations/CLIENT_WALKTHROUGH.md) and [technical](presentations/TECHNICAL_WALKTHROUGH.md) walkthroughs |

## Reproducible local checks

The verified host used macOS 27.0.1 arm64 on Apple M4, Python 3.12.12, uv 0.11.8, Node 26.5.0, npm 11.17.0 and pinned Playwright Chromium. Other declared Node versions, operating systems and browsers were not tested here.

| Command | Recorded result |
| --- | --- |
| `make setup` | Locked backend sync and clean npm install passed; npm lifecycle scripts disabled. |
| `make migrate` | Applied/confirmed SQLite schema `0001_snapshots`. |
| `make ingest-fixtures` | Offline synthetic import completed 69 windows, 744 expected forecast targets; content input hash `66a2bff1392315588edddfefab98bf59a72da47b5806d85e54b9ad1ecd8338eb`. Snapshot IDs can change on reimport. |
| `make check` | Python lint/format and 151 backend tests passed; frontend lint/type checks, 78 tests and production build passed after preview removal. |
| `make test-browser` | 19 real-data Chromium tests passed, with no unexpected/flaky/skipped cases. Nine axe scans reported zero violations across both views at 320/768/1024/1440px and the data-details dialog. The suite used isolated API/web ports 4285/4284. |
| `make test-ui-runtime` | Eight real-API/fixture production view/width cases passed at 320/768/1024/1440px; maximum CLS 0.000295 and frame-gap p95 16.8 ms on this host. |
| `make benchmark-api` | Five warmups and 100 sequential full-January accuracy HTTP requests, each with 744 rows, passed the 1,000 ms local p95 target. Observed p50 129.353 ms, p95 134.942 ms, maximum 139.705 ms. No source download was included. |
| `make audit-january` | Active live snapshot `9e2b992d3cb943aa9a82d4c3e71fd68f`: 744 expected, 744 forecast selected, 744 exact-time actual references complete and 744 matched. |
| `make audit-security` and focused checks | Dated [security audit](evidence/security-release-audit.json) records zero known uv/npm advisories in selected graphs, valid npm registry signatures, Ruff security rules and 66 scoped tests. |
| `backend/.venv/bin/python scripts/reconcile_live_exports.py` | Downloaded pinned live JSON and CSV over an owned local API; independently parsed/recomputed 744 Accuracy rows and checked 24 Decision export rows. Policy, row, source and actual-constituent lineage parity passed. |

`make ingest-january` originally downloaded the full source windows and the documented live snapshot was later published from saved raw inputs under ADR-002 without another network request. [The import record](evidence/elexon-january-import.json) retains both acquisition and replay identities, original retrieval timestamps, request URLs, hashes and all 69 window outcomes. The current local `data/` directory contains that active live snapshot. Fixture data is separate under ignored `data/fixtures/`. The API never imports on read.

## January result and demonstration

For the default 09:30 `Europe/London` decision cutoff, January has 31 decision dates and 744 hourly targets, delivered 2 January-1 February. The live snapshot contains 23,680 downloaded rows, 19,352 scoped semantic observations, and all 1,488 expected FUELHH `WIND` half-hours. Observed benchmark coverage is 744/744 with zero unresolved or missing targets in this retrieval. The independent CSV recomputation matches the API exactly: MAE 1,995.5685483870968 MW, RMSE 2,498.8245110107187 MW, bias +1,727.9825268817203 MW.

A real cutoff demonstration uses the 15 January decision for 16 January delivery. At 09:00 the 00:00 target selects 7,398 MW from the 07:30 publication; at 09:30 it selects 7,472 MW from the 09:30 publication. All 24 selected hourly values for that delivery day change between those cutoffs. This demonstrates why a latest-now lookup would be wrong for historical replay. Accuracy is retrospective and does not present outturn as information available at decision time.

## Limits and deferred work

The benchmark compares each hourly WINDFOR target with the FUELHH half-hour average starting at the same timestamp. WINDFOR's physical averaging interval is unverified, so these metrics are a timestamp-reference benchmark, not physically equivalent hourly energy accuracy. `temporal_reference_mismatch` is retained in every comparison row and the limitation appears in UI/API/CSV/presentations. Source history is bounded by the recorded search from 25 December 2025; 69 successful windows and complete target coverage do not prove exhaustive prior forecasts, every later actual revision, or final settlement truth.

The configurable 09:30 cutoff, January scope and local-only delivery are documented assignment assumptions, not client-approved trading rules. No MWh, purchase recommendation, demand, prices or financial saving is calculated. The optional FR05 UI revision viewer is DEFERRED (an eligible-only backend route exists); FR10 p90/time-of-day breakdowns are DEFERRED. Authentication, TLS, public hosting, multi-browser certification, complete accessibility certification and exhaustive penetration testing are outside this local baseline. The directory has no Git repository; no commit or publication has been performed.
