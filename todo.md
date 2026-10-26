# Project todo

Last updated: 27 October 2026. Current phase: T01-T12 local analytical baseline and Docker package VERIFIED; public source repository IMPLEMENTED; assignment submission PARTIAL. The attached challenge still requires a public Vercel app, a two-part video and form submission. The [assignment audit](docs/ASSIGNMENT_AUDIT.md) separates these from local verification.

This is the progress tracker for [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Task IDs, scope, dependencies, acceptance criteria, and verification commands come from that plan. Keep IDs stable and link evidence when updating status.

## Preparation completed

- [x] Create the [PRD](docs/PRD.md), [architecture](docs/ARCHITECTURE.md), and [implementation plan](docs/IMPLEMENTATION_PLAN.md).
- [x] Record [source research](docs/SOURCE_RESEARCH.md), the [sample audit](docs/evidence/elexon-sample-audit.json), the [API contract audit](docs/evidence/elexon-api-contract-audit.json), and [ADR-001](docs/decisions/0001-mvp-baseline.md).
- [x] Create [AGENTS.md](AGENTS.md), this tracker, and project-local [memory.md](memory.md).

Preparation is documentation and source reconnaissance. It does not complete T01 or demonstrate application behavior.

## UI design review

- [x] Draft [UI mockup DRAFT 01](design/ui-mockup.html) with Decision and Accuracy views and preview states.
- [x] Create the empty [frontend placeholder](frontend/src/DesignPlaceholder.tsx), preserving the existing application shell.
- [x] Record the user's instruction to implement from the supplied mockups, superseding the frontend hold.
- [x] Create [UI_DESIGN.md](docs/UI_DESIGN.md) before delegating frontend implementation.
- [x] Build the interactive Decision/Accuracy UI with SCSS and responsive motion, then connect it to pinned analytical API responses.

The original HTML remains a design artifact. The React application reads stored data. The user later removed the interactive mockup preview from the app; [current browser evidence](docs/BROWSER_TEST_REPORT.md) covers the real-only frontend.

## Implementation checklist

| Done | ID | Task | Status | Dependencies / entry condition | Evidence |
| --- | --- | --- | --- | --- | --- |
| [x] | T01 | Validate the source and comparison contract | VERIFIED | Source parameter research and named benchmark decision | [Source-contract note](docs/T01_SOURCE_CONTRACT.md), [comparison research](docs/COMPARISON_POLICY.md), [ADR-002](docs/decisions/0002-timestamp-matched-reference.md); physical equivalence remains an explicit limitation |
| [x] | T02 | Create a runnable project and test foundation | VERIFIED | Complete on the recorded host | Locked `make setup`; backend/frontend checks and build in [release validation](docs/RELEASE_VALIDATION.md) |
| [x] | T03 | Import one decision day's data into an immutable snapshot | VERIFIED | T01/T02 | SQLite migration, live sample, raw provenance, fixture replay, failure rollback and tests; [sample evidence](docs/evidence/elexon-sample-import.json) |
| [x] | T04 | Serve the one-day forecast as it stood at cutoff | VERIFIED | T03 | `/forecast` and `/data-status`; cutoff equality, conflict, gap and pinned snapshot tests |
| [x] | T05 | Build the one-day decision interface | VERIFIED | T04 | Stored Decision view, chart, rows, provenance, filters and browser cases |
| [x] | T06 | Implement validated alignment and error calculations | VERIFIED | T01/T04; adopted policy | Exact-time half-hour reference, conservative actual revisions, metrics and unit fixtures; temporal limitation displayed |
| [x] | T07 | Expose retrospective accuracy and daily breakdowns | VERIFIED | T06 | `/accuracy` month/grid/metrics/null/pinning tests |
| [x] | T08 | Backfill and audit the full January decision scope | VERIFIED | T01/T03 | 69 successful live windows, 744 forecast targets, 1,488 actual half-hours; [January evidence](docs/evidence/elexon-january-import.json), month audit and failure tests |
| [x] | T09 | Build the accuracy workflow | VERIFIED | T05/T07 | Real retrospective charts, error bars, coverage, daily rows, source details and browser cases |
| [x] | T10 | Export reproducible analytical rows | VERIFIED | T04/T07 | Pinned full-grid CSV, source lineage, formula safety, fixture parity and [live reconciliation](docs/evidence/live-export-reconciliation.json) |
| [x] | T11 | Complete failure-state and interaction behavior | VERIFIED | T05/T09 | Offline fixtures, missing/conflict, failed refresh, unknown snapshot, stale-response and accessibility cases |
| [x] | T12 | Verify and package the assignment | VERIFIED | T08/T10/T11 | Clean setup/check, live month audit, browser/runtime/security checks, 100-request benchmark, independent CSV reconciliation, [release record](docs/RELEASE_VALIDATION.md) and both presentations |

The Done cell is checked only for tasks whose acceptance evidence has passed. Source and physical interpretation limits remain visible even when the selected application policy is implemented.

## Next work

1. Reviewer: run the saved live snapshot or the separate synthetic fixture with the [README](README.md) commands and use the [client](docs/presentations/CLIENT_WALKTHROUGH.md) or [technical](docs/presentations/TECHNICAL_WALKTHROUGH.md) outline.
2. If Elexon clarifies WINDFOR's physical interval or the client supplies an actual buying cutoff, version the policy and regenerate the affected snapshot/tests before changing displayed claims.
3. Complete Vercel production deployment and signed-out URL checks, then record the unlisted video and submit the form as tracked in the [assignment audit](docs/ASSIGNMENT_AUDIT.md). Optional FR05 UI viewer and FR10 extra statistics remain DEFERRED.

The user corrected the earlier UI-only interpretation: delivery requires the real backend and full application. The application adopts the documented timestamp-reference benchmark while retaining the physical source ambiguity.

## Open decisions and dependencies

| Item | Working default or current state | Effect |
| --- | --- | --- |
| Meaning of January | Decision dates 1-31 January; delivery 2 January-1 February | Documented assumption; revise if assessor clarifies |
| Buying cutoff | Configurable 09:30 Europe/London | Demo assumption; does not block setup |
| Forecast interval semantics | Hourly-average meaning unverified; [ADR-002](docs/decisions/0002-timestamp-matched-reference.md) adopts an exact-time half-hour benchmark | Visible limitation; a new physical interpretation needs a new policy and snapshot |
| Query bounds, history extent, revisions | Requested live January windows succeeded; search begins 25 December 2025 and settlement dates end 1 February | Observed target coverage does not prove exhaustive historical revisions or final settlement truth |
| Submission deadline | Not supplied | No delivery-date commitment |
| Hosted URL requirement | The attached assignment requires a public Vercel or Heroku sample app; this delivery chooses Vercel | Blocks final submission until the production URL works signed out |
| UI direction | User instructed full backend plus mockup-inspired SCSS frontend | Stored-data workflow implemented; interactive mockup preview removed at the user's request |

## Should features after the Must baseline

- [ ] FR05: eligible forecast-revision viewer is DEFERRED in the UI; an eligible-only backend route is implemented.
- [ ] FR10: p90 absolute error and delivery-time-of-day breakdowns are DEFERRED.

These are Should features in the PRD; neither is needed to satisfy the Must baseline.

## Completion record

For each completed or interrupted task, record: date, status, changed files, verification command and result, fixture or snapshot identity where relevant, remaining issue, and next step. Keep logs concise and link larger evidence files. Do not paste credentials or full source payloads here.

### 26 October 2026: first implementation slice

- T02 PARTIAL: added backend package, exact dependency pins/lock, typed process-health endpoint, strict local CORS, unknown-query rejection, environment reference, Makefile and ignore rules. `make setup-backend` and `make check-backend` passed on Python 3.12.12; 7 tests passed. The testing agent also installed the backend in a fresh temporary directory and reran tests/lint/format successfully. This verifies one host with a clean environment, not every supported machine.
- Frontend agent created preliminary Vite/React/TypeScript configuration, lock, shell and styles; testing agent authored six smoke tests. The frontend agent reported six passing tests, lint, type checking and build before the user requested the hold. No browser/visual inspection occurred. Preserve files and wait for the design identifier; combined T02 verification remains incomplete.
- T01 PARTIAL: added `scripts/audit_source_contract.py`, [dated evidence](docs/evidence/elexon-t01-source-checks.json), and [source-contract/fixture specification](docs/T01_SOURCE_CONTRACT.md). All 8 requests succeeded. The three sampled delivery days each have 24 eligible forecast targets and 48 WIND half-hours. Alignment and late-revision completeness remain unresolved; no metrics or snapshot exists.
- No Git initialization, commit, publication, full-month import, or deployment. All task checkboxes remain unchecked because neither T01 nor T02 meets its complete acceptance gate.

### 26 October 2026: UI delivery and security verification

- UI preview VERIFIED: [handoff](docs/UI_DESIGN.md) and React Decision/Accuracy screens follow the supplied mockups. User requested SCSS, so styling uses `styles.scss` and a shared token module; compiled styles match the earlier rendering. Original design artifacts remain unchanged.
- T02 VERIFIED: clean `make setup` and full `make check` pass with exact locks and disabled npm dependency scripts. Backend 49 tests and frontend 28 tests pass; lint/type checks and production build pass. Node 26.5.0/npm 11.17.0, Python 3.12.12, macOS arm64 are the recorded verification host.
- `make test-browser` equivalent npm script passed all 20 tests after SCSS conversion: both views at 320/768/1024/1440, 16 zero-violation axe scans, keyboard/modal behavior, filters/history, state previews, health errors/retry and motion checks. Native modal focus wrap was found by browser testing and fixed before the final pass.
- Production runtime script passed 8 cases: no page overflow, browser errors, external assets, ongoing animation or measured initial layout shift; local document readiness 23.7-43.7ms and frame-gap p95 at most 16.8ms on the recorded host. These are UI measurements, not NFR02 API benchmarks. [Evidence](docs/evidence/ui/production-runtime.json).
- Backend hardening and security tests: 21 source-aware and 21 real-Uvicorn black-box probes plus prior health checks pass. [Security review](docs/SECURITY_REVIEW.md) records tested boundaries and excluded future features. npm/uv advisory checks found no known vulnerabilities; npm signature check reported no invalid/missing entries.
- T05/T09/T11 stay PARTIAL pending analytical services and immutable snapshots. No full-month data, measured accuracy, CSV parity, deployment, presentation or Git publication is claimed. Next: T03 ingestion and T01 semantics research.

### 26 October 2026: completed local application and release verification

- T01 VERIFIED: primary-source research did not establish WINDFOR hourly-average semantics. [ADR-002](docs/decisions/0002-timestamp-matched-reference.md) adopts a labelled exact-time half-hour reference benchmark; this resolves the application rule while preserving the physical limitation. Source bounds, actual-revision samples and fixture specifications are recorded separately.
- T03-T04 VERIFIED: fixed-host WINDFOR/FUELHH `WIND` CLI, SQLite migration, immutable membership/raw lineage, conservative per-target cutoff selection and read-only forecast/status routes. Live sample and deterministic fixture imports, transport/schema failure rollback, conflicts, zero, revisions and source provenance were tested.
- T05-T07, T09 VERIFIED: default Decision and Accuracy views use pinned API responses. Python supplies exact-time reference alignment, daily/pooled metrics and reasons. SCSS charts/tables show gaps and the comparison note; Decision contains no future actuals. Browser tests cover both views, responsive behavior and stale-response ordering.
- T08 VERIFIED: the live January acquisition completed all 69 requested windows; the final saved snapshot `9e2b992d3cb943aa9a82d4c3e71fd68f` has input hash `dfebf7e8895557c162096eb06e3cf1fcf17971e5dbd29974290310de231bb94d`. Month audit reports 744/744 matched at 09:30. A regression prevents a one-day snapshot from being presented as a full-month audit.
- T10 VERIFIED: pinned full-grid CSV passes fixture tests and [independent live HTTP reconciliation](docs/evidence/live-export-reconciliation.json): 744 Accuracy rows, 24 Decision rows, policy/source/constituent parity, exact recomputed MAE/RMSE/bias and no actual-data leakage into Decision.
- T11-T12 VERIFIED: `make setup`, `make migrate`, `make ingest-fixtures`, `make check` (151 backend and 82 frontend tests), `make test-browser` (35 Chromium cases, 24 axe scans with zero reported violations), `make test-ui-runtime` (eight responsive production cases), `make benchmark-api` (100 month requests, p95 134.942 ms versus 1,000 ms target), `make audit-january`, and `make audit-security` passed. [Security review](docs/SECURITY_REVIEW.md) adds scoped black-box/white-box, dependency, CSV, and browser evidence with limits. [Live screenshots](docs/UI_VALIDATION.md), [release validation](docs/RELEASE_VALIDATION.md), and both 5-7 minute presentation outlines are complete.
- The result is a local assignment build. Physical averaging equivalence, exhaustive source-revision history, final settlement truth, public deployment, and optional FR05/FR10 UI/statistics remain outside verified claims. No Git repository, commit or publication was created.

### 26 October 2026: README maintenance

- Documentation VERIFIED: [README.md](README.md) now maps the source, tests, design, evidence and generated directories; gives live-snapshot and offline-fixture startup steps; and explains the workspace, API, import commands, checks and analytical limits. All 28 relative README links resolve, documented Make targets were checked against the current Makefile, and the required prose audit reported no suspicious Unicode and low stylometry density. No application behavior changed; the T01-T12 status above remains current.

### 26 October 2026: local entry routes

- Local entry behavior VERIFIED: `GET /` on the backend redirects to the UI on port 5173, and `GET /health` aliases the process-only `/api/v1/health` response. This addresses the reported 404s for `/` and `/health`; browser icon probes from the earlier API page were incidental. The new route test, 62 focused health/security checks, a live browser redirect check, and full `make check` (151 backend and 82 frontend tests) passed. The analytical API and snapshot behavior did not change.

### 26 October 2026: real-only frontend and browser review

- UI change VERIFIED: removed the interactive mockup preview controls, route state and preview-only React components/tests after the user's direct feedback. The original `design/` mockup and historical empty placeholder remain references. An old `mode=preview` link now shows an unsupported-link warning, and Reset returns to stored data.
- Browser review VERIFIED: the ChatGPT in-app browser exercised the saved live snapshot `9e2b992d3cb943aa9a82d4c3e71fd68f` across Decision, Accuracy, filters, provenance, CSV, history and data details. Both local servers had stopped at the start; restarting them restored data requests. [Report and screenshots](docs/BROWSER_TEST_REPORT.md) separate that availability issue from app behavior.
- Final checks VERIFIED: `make check-backend` passed 151 tests; `make check-frontend` passed 78 tests, lint, types and build; isolated Chromium passed 19 real-data cases and nine axe scans; `make test-ui-runtime` passed eight production cases; `make audit-security` found no known vulnerabilities in the selected Python/npm dependency graphs. Historical 35-case preview-era results above remain a dated record, not the current suite count.
- Next step: demonstrate the real application from the README. Physical interval equivalence, exhaustive revision history, public deployment and optional FR05/FR10 remain outside the verified local scope.

### 26 October 2026: simplify the live workspace header

- UI change VERIFIED: removed the redundant snapshot strip and breadcrumb/review badge row from both real-data views. The page heading now leads the workspace; source mode and snapshot details remain in the context card and Data details, and Accuracy still explains its comparison with later wind generation.
- Verification: inspected the live saved snapshot in the ChatGPT browser after the change, refreshed both [Decision and Accuracy screenshots](docs/BROWSER_TEST_REPORT.md), passed `make check-frontend` (78 tests, lint, types and build) and the isolated 19-case Chromium suite. Production runtime evidence was rerun for eight view/width cases. No backend contract or analytical policy changed.

### 26 October 2026: applied-cutoff note follow-up

- UI copy VERIFIED: a shared scope note shows the applied cutoff in both loading and loaded views and identifies 09:30 UK as the demo default. The loaded note uses the API response cutoff. This resolves the 09:00 mismatch recorded in [UI validation](docs/UI_VALIDATION.md#additional-ui-audit-26-october-2026).
- Verification: 79 frontend tests, lint, type checking and build passed; 20 isolated Chromium cases passed, including a non-default cutoff assertion; eight production runtime cases passed. The live 09:00 Accuracy view was inspected with recalculated metrics and no browser console warnings or errors. No backend policy, snapshot or analytical data changed.

### 26 October 2026: backend test audit

- Backend analytical/API behavior VERIFIED in the tested local scope: `make check-backend` passed 151 tests plus Ruff lint/format; a separate Ruff security scan and `uv audit` passed. Saved live January audit returned 744/744 matches. Fresh offline fixture import reproduced its designed 741/744 matches and gap reasons. Read-only HTTP probes passed cutoff, separation, error-status, revision-eligibility, and snapshot-stability checks.
- [Fresh benchmark](docs/evidence/backend-test-benchmark-2026-10-26.json) passed the 1,000 ms local p95 target at 138.06 ms for 100 warm pinned January requests. [Fresh CSV reconciliation](docs/evidence/backend-test-reconciliation-2026-10-26.json) matched 744 Accuracy and 24 Decision rows, policies, lineage and metrics. The [report](docs/BACKEND_TEST_REPORT.md) separates these results from source and deployment limits.
- Backend observability was PARTIAL at the time of this audit. It was implemented and verified in the follow-up below. No backend code or saved live snapshot was modified during the audit itself.

### 26 October 2026: backend diagnostics follow-up

- Backend observability VERIFIED in the tested local scope: JSON-line HTTP events include a response-correlated request ID, bounded validated context, duration and outcome. The import CLI emits per-window attempts/counts and distinct failure events, plus the published snapshot and manifest hash. [Backend report](docs/BACKEND_TEST_REPORT.md) records the implementation and limits.
- Verification: `make check-backend` passed Ruff lint/format and 155 tests; Ruff security rules passed. Owned offline CLI and Uvicorn subprocesses emitted the expected events, with matching `X-Request-ID` headers. The isolated Chromium suite passed 20 cases. The [post-change benchmark](docs/evidence/backend-logging-benchmark-2026-10-26.json) measured 133.15 ms p95 over 100 warm full-January requests, below the 1,000 ms local target. No fresh Elexon download or public-hosting check was performed.
- Frontend integration VERIFIED after the change: `make check-frontend` passed lint, types, 79 tests and build; 20 isolated Chromium cases passed with the real API and a synthetic snapshot. An owned production-preview browser run loaded Decision and Accuracy from the saved live January snapshot, observed 200 responses with `X-Request-ID`, and reported no browser page errors.

### 27 October 2026: assignment alignment audit

- Local assembly VERIFIED: `make check` passed 155 backend and 79 frontend tests, lint, types and build. An isolated Chromium run passed 20 cases after the default browser command found port 8000 occupied. Direct saved-snapshot API checks returned 200 for health, status, Decision and full January Accuracy, with 744/744 matched benchmark rows.
- Delivery PARTIAL: the attached brief's Docker, public Vercel, anonymous public GitHub, unlisted video and form requirements were compared with the workspace. None is evidenced as completed. Docker CLI exists, but its daemon was unavailable, so no image test ran. [Report](docs/ASSIGNMENT_AUDIT.md) records the missing components and Vercel path; [video script](docs/presentations/ASSIGNMENT_VIDEO_SCRIPT.md) stays under ten minutes. README now discloses AI assistance and states the missing live URL plainly.
- Next: implement and verify the Docker/Vercel package against the reviewed immutable snapshot, then publish and test the production/repo/video URLs before submitting the form. Do not relabel the local T01-T12 checks as hosted validation.

### 27 October 2026: Docker and public repository follow-up

- Docker package VERIFIED locally: `Dockerfile.vercel` builds the locked React and Python app, serves the UI and API from one port, and includes a reviewed read-only live snapshot. The build checked SQLite integrity, snapshot and manifest identity, and all 69 raw response hashes. The container ran as UID 10001; UI, static asset, health, status, Decision, 744-row Accuracy and 24-row Decision CSV returned 200. A simulated Vercel Host returned 200. A real Chromium run loaded both views without page errors.
- Regression checks VERIFIED: `make check` passed 157 backend and 79 frontend tests, lint, types and build. The isolated browser suite passed 20 cases after packaging. These are local checks; Vercel deployment is still PARTIAL.
- Public repository IMPLEMENTED: reviewed source and the immutable deployment inputs were pushed to [vsuman00/r8m4q2v6](https://github.com/vsuman00/r8m4q2v6). Generated local data, dependencies, caches and test output remain ignored. Next: import this repository into Vercel, verify the production URL signed out, then record and submit the video and form.
