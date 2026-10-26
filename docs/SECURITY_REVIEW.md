# Security review: local analytical application

Reviewed 26 October 2026. Scope: the loopback FastAPI read API, separate Elexon import CLI, SQLite snapshot and lineage reads, CSV exports, frontend data handling, and installed locked dependencies. The [release audit](evidence/security-release-audit.json) records exact commands, source hashes, results, and limits. These checks do not establish that every defect is absent or that the app is ready for public hosting.

## Trust boundaries and controls

| Boundary | Main risk | Implemented control and check |
| --- | --- | --- |
| HTTP access | Foreign Host/origin, writes, malformed or oversized requests | Loopback binding, exact trusted Hosts and two local CORS origins, GET-only product routes, 2 KB raw-query cap, strict parameter/date/snapshot validation. Real-Uvicorn black-box probes cover methods, Host/origin lookalikes, traversal, injection strings, parser rejection and missing-data behavior. |
| Browser response | Script injection, unintended disclosure, stale data | React renders source text as text; API response shapes, URL state and stale responses are checked. API emits `nosniff`, frame denial, no-referrer, no-store, restrictive JSON CSP and generic 500 errors. Production UI uses a self-only CSP without inline/eval scripts; runtime verification blocks an injected inline script. Decision responses and CSV omit retrospective actuals and errors. |
| Data storage | Cross-snapshot data or SQL injection | HTTP repository opens SQLite with `mode=ro`, queries explicit snapshot membership, and binds values. The sole reviewed Ruff S608 suppression constructs only `?` placeholders; all IDs are bound separately. API startup and no-dataset requests neither migrate nor create storage. |
| Elexon transport | Arbitrary fetch target, redirect or unbounded retry | Only fixed HTTPS WINDFOR and FUELHH `WIND` stream requests are accepted. The client does not follow redirects, uses a 20-second timeout, at most three attempts and a 10-second total retry delay budget per window. Imports run through the CLI, never a browser GET. |
| Import publication | Malformed payload replaces valid data or loses provenance | Raw responses are hashed before parsing; schema failures abort publication. Per-window outcomes, semantic duplicates/conflicts and actual revisions remain recorded. Candidate validation precedes the atomic active-pointer switch; failed imports retain the previous snapshot. Fixture failure/replay tests cover this. |
| CSV | Spreadsheet formula execution or misleading numeric values | Free-text fields beginning with formula characters are prefixed safely, while negative numeric errors stay numeric. Full-grid export pins a snapshot and preserves policy, reason, publication and raw constituent lineage. Fixture tests and independent live HTTP reconciliation compare CSV with JSON. |
| Dependencies | Known published advisories or unsigned packages | Exact uv/npm locks, disabled npm lifecycle scripts, `uv audit`, `npm audit`, npm registry signature check and lock-consistency check. Results are dated and can change. |

The API has no login, session, upload or writable product route. `GET /` redirects only to the fixed local UI address, and `/health` aliases the process-only versioned health route. Neither accepts a user-supplied redirect target or triggers an import. It uses public source data; it does not store client account details. The local operator and local data directory are trusted. A public deployment would need a separate TLS, authentication/authorization, operational monitoring, access and abuse-resistance design.

## Verification

On the recorded Python 3.12.12/macOS arm64 and Node 26.5.0/npm 11.17.0 host:

- At this review, 151 backend and 78 frontend tests passed with lint, Python formatting, TypeScript checking and production build after the mockup preview was removed. A later [backend logging follow-up](BACKEND_TEST_REPORT.md#structured-logging-follow-up-verified) passed 155 backend tests; this dated security review's other results remain unchanged.
- A focused suite of 66 HTTP security, source-aware and CSV tests passed. Real black-box tests own and terminate a Uvicorn subprocess on an ephemeral loopback port; they do not probe unrelated services.
- Ruff's `S` security rules, `uv lock --check`, and a targeted 47-file source pattern review passed. No hard-coded key shape or dynamic execution/HTML injection sink was found in the recorded patterns. The SQL placeholder-only suppression was reviewed directly.
- `uv audit` found no known vulnerabilities or adverse statuses in 33 selected packages. `npm audit` found zero advisories in its 281-package graph; registry signature output contained no invalid or missing entries.
- The current isolated browser run passed 19 real-data Chromium flows; nine axe scans reported no violations across stored pages at 320/768/1024/1440px and the settled data-details dialog. `make test-ui-runtime` passed all eight stored-fixture production view/width cases, strict CSP and inline-script rejection, no page overflow/external assets/browser errors, and small measured layout shift. The current `make audit-security` run reported no known vulnerabilities in the selected Python and npm graphs. [Browser evidence](BROWSER_TEST_REPORT.md) records details and limits.
- The independent [live CSV reconciliation](evidence/live-export-reconciliation.json) parsed the downloaded 744-row accuracy export and 24-row forecast export, checked source/policy/constituent parity, and recomputed metrics from CSV values.

The historical [foundation review](evidence/security-backend-review.json) tested only the earlier process-health phase. The release audit supersedes it for the current scope; the old artifact remains as a dated record.

## Limits

The abuse probes and static rules are targeted checks, not exhaustive fuzzing or a penetration test. No Git history exists for historical secret scanning. Advisory databases and npm signatures cannot detect every supply-chain problem. No rate limiter or volumetric denial-of-service test was added for this local assignment. Provider payload size and every malformed remote input were not stress-tested. The source comparison's physical averaging equivalence and exhaustive historical revision availability are analytical limits, not solved by security tests. Public hosting and all operating-system access controls are outside this local verification.

## Container follow-up, 27 October 2026

The single-port Docker image now builds the locked React and Python packages and verifies the reviewed live SQLite snapshot, its manifest and all 69 saved raw hashes during the build. The runtime uses an unprivileged user; the packaged data is read-only. The API still opens SQLite with `mode=ro`, and browser requests do not invoke the import CLI. Local container probes returned 200 for the UI, static asset, health, status, Decision, Accuracy and pinned CSV; a simulated `VERCEL_URL` Host was accepted. API and UI responses retained separate restrictive CSPs. A real Chromium run loaded Decision and Accuracy from the container with no page errors. `make check` passed 157 backend and 79 frontend tests, and the isolated 20-case browser suite passed after packaging. These checks do not establish Vercel runtime behavior, production TLS, abuse resistance or public access.
