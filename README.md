# GridBricks

GridBricks is a local web application for reviewing the Elexon national wind forecast available at a historical day-ahead buying cutoff and comparing it with reported wind generation. It has a React/TypeScript frontend styled with SCSS, a read-only FastAPI backend, SQLite snapshot storage, and a separate Python import CLI. The UI follows the supplied [mockup](design/ui-mockup.html) and displays stored analytical data.

The application covers decisions on **1-31 January 2026** and delivery on **2 January-1 February 2026**. The default buying cutoff is **09:30 Europe/London**, a configurable demo assumption. There is no API key or client data requirement.

## Project layout

| Path | Purpose |
| --- | --- |
| [`frontend/`](frontend/) | React/Vite application. `src/App.tsx` coordinates the workspace; `src/components/` contains filters, charts, tables and data details; `src/api.ts`, `apiValidation.ts`, `useData.ts` and `useWorkspace.ts` handle API responses and URL state. `src/styles.scss` and `src/styles/_tokens.scss` are the application SCSS sources. `e2e/` contains Playwright browser tests; `scripts/verify-runtime.mjs` checks production UI behavior. `package.json` and `package-lock.json` pin dependencies. |
| [`backend/src/gridbricks/`](backend/src/gridbricks/) | Python application. `main.py` creates the FastAPI app; `api/` owns read routes and CSV; `analytics/` owns cutoff selection, actual alignment and metrics; `sources/` fixes the Elexon request boundary; `ingestion/` validates and imports data; `storage/` owns SQLite access; `cli.py` runs migrations, imports and audits; `config.py` resolves the data directory. |
| [`backend/migrations/`](backend/migrations/) | Alembic migration environment and versioned SQLite schema. |
| [`backend/tests/`](backend/tests/) | Deterministic unit, integration, source, snapshot, API, CSV and security tests. Its `fixtures/` are checked-in synthetic test specifications, not observed Elexon data. |
| [`Dockerfile.vercel`](Dockerfile.vercel), [`.dockerignore`](.dockerignore), [`deployment/data/`](deployment/data/) | Single-container Vercel build and its reviewed, immutable live January SQLite snapshot, manifest and 69 saved source responses. The container serves the built frontend and read-only API on one port. |
| [`design/`](design/) | Original HTML mockup and Decision/Accuracy reference images. These are design references, not the running application. |
| [`docs/`](docs/) | [PRD](docs/PRD.md), [architecture](docs/ARCHITECTURE.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md), [comparison policy](docs/COMPARISON_POLICY.md), API contract, ADRs, [browser test report](docs/BROWSER_TEST_REPORT.md), [release validation](docs/RELEASE_VALIDATION.md), [security review](docs/SECURITY_REVIEW.md), [assignment audit](docs/ASSIGNMENT_AUDIT.md), evidence and presentation material. |
| [`scripts/`](scripts/) | Source-contract audit, local API benchmark, independent live CSV reconciliation and packaged-snapshot verification scripts. |
| `data/` | Generated local SQLite database, raw Elexon responses and snapshot manifests. `data/fixtures/` holds a separate generated synthetic dataset. This directory is ignored and may not exist in a fresh copy. |
| [`Makefile`](Makefile) | Setup, import, development, checks, benchmark and audit commands. |
| [`.env.example`](.env.example) | Optional environment reference. It is **not** loaded automatically. |
| [`AGENTS.md`](AGENTS.md), [`todo.md`](todo.md), [`memory.md`](memory.md) | Project instructions, task/evidence status and a short project-local summary. |

Generated `frontend/node_modules/`, `frontend/dist/`, `backend/.venv/`, browser results, caches and `data/` are local artifacts. The source files and lockfiles above are what a fresh setup needs.

## Requirements

- `make`, `uv`, and Node.js/npm. The backend requires Python **3.12**; `uv` installs/selects it through `make setup` if available from the configured toolchain. The frontend declares Node `^22.22.2 || ^24.15.0 || ^26.0.0` and npm `>=10`.
- Internet access for the first locked dependency installation. A live January import also needs access to Elexon. Offline fixture use does not contact Elexon after dependencies are installed.
- A browser. The recorded checks used Chromium on macOS arm64 with Python 3.12.12, Node 26.5.0, npm 11.17.0 and uv 0.11.8; other supported hosts and browsers have not been verified here.

Run all commands below from the project root.

## Start the application

Install the locked backend and frontend dependencies:

```bash
make setup
```

Choose one dataset:

1. **Use a saved live snapshot:** If `data/gridbricks.sqlite3` and its raw/snapshot files are already present, no import is needed. The current workspace contains a saved January snapshot. For a fresh copy, create and import it with `make migrate` followed by `make ingest-january`. This downloads Elexon WINDFOR and FUELHH `WIND` records and can take time.
2. **Use an offline synthetic snapshot:** Run `make ingest-fixtures`. It writes a separate dataset under `data/fixtures/` with deliberate gaps and conflicts for demonstration. The UI labels it synthetic.

Start the two servers in separate terminals. For the saved live dataset:

```bash
make backend-dev
```

```bash
make frontend-dev
```

For the synthetic dataset, start the backend with its data directory set explicitly, then start the same frontend command in another terminal:

```bash
GRIDBRICKS_DATA_DIR="$PWD/data/fixtures" make backend-dev
```

```bash
make frontend-dev
```

Open **http://127.0.0.1:5173**. The frontend proxies `/api` to FastAPI at `127.0.0.1:8000`. Opening `http://127.0.0.1:8000/` also redirects to the UI when both servers are running. The backend does not migrate or download data when it starts or handles a browser request. If it starts without a snapshot, the UI explains that a dataset must be imported. The earlier mockup preview is no longer part of the application.

### Using the workspace

- In **Decision**, select a January decision date and cutoff. The chart and interval table show only the latest unambiguous forecast publication available at or before that cutoff. Publication time, age, lead time, status and raw-source lineage can be inspected. Future actuals are not shown in this view.
- In **Accuracy**, select a January date range and cutoff. The charts, pooled MAE/RMSE/bias, coverage, interval table and daily table are retrospective. Missing or conflicting inputs remain gaps; zero generation stays zero.
- The URL pins the chosen snapshot, view and applied filters. Export CSV downloads the same full target grid, policies, states and provenance used for the displayed result. A refresh of the active dataset does not silently change an already pinned result.
- **Data details** shows the source, snapshot, import and comparison policy. A failed refresh does not replace the previous valid snapshot.

### Other import and audit commands

| Command | Effect |
| --- | --- |
| `make migrate` | Apply the versioned SQLite schema in the default `data/` directory. |
| `make ingest-sample` | Import the 15 January decision and 16 January delivery from Elexon into the default data directory. |
| `make ingest-january` | Import all January decision dates and the corresponding delivery coverage from Elexon. |
| `make ingest-fixtures` | Build a separate, repeatable synthetic January dataset without Elexon access. |
| `make audit-january` | Report full January expected/selected/matched counts, gaps, policies and the active default snapshot. It audits all January decisions even if a narrower snapshot is active. |

`GRIDBRICKS_DATA_DIR` can point the backend or CLI at another saved data directory. The CLI also accepts `--data-dir`. `.env.example` documents the variable but is not a dotenv loader.

## Data and comparison policy

Only WINDFOR forecasts and FUELHH records with `fuelType=WIND` enter the analysis. For each hourly delivery target, the backend chooses the greatest `publishTime <= cutoff` separately. Equal-cutoff publications are eligible. A conflicting newest publication remains unresolved; the app does not choose by row order or fall back silently. Raw responses, revisions, retrieval times and snapshot membership are retained.

Accuracy uses the named [`timestamp_matched_halfhour_reference_v1` policy](docs/COMPARISON_POLICY.md): one WINDFOR hourly target at time `t` is compared with the FUELHH half-hour average beginning at `t`, selected from the pinned snapshot. The adjacent half-hour is stored but is not averaged or counted as another observation. **WINDFOR's physical averaging interval is unverified**, so these are timestamp-matched benchmark metrics, not a claim of physically equivalent hourly energy accuracy. Every accuracy response and export states this limitation. Error is forecast minus actual reference, in MW; MAE, RMSE and bias pool matched intervals. No matches produce null metrics. The app makes no purchase recommendation or financial-savings claim.

The saved live January snapshot and its bounded retrieval are documented in [import evidence](docs/evidence/elexon-january-import.json): 69 successful requested windows, 744 expected forecast targets and 1,488 expected actual half-hours observed. At the default cutoff, 744/744 timestamp-reference comparisons match. This does not prove exhaustive historical revisions or final settlement truth. The synthetic fixture intentionally includes missing and conflicting records.

Contains BMRS data © Elexon Limited copyright and database right 2026. The [Elexon BMRS open data licence](https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/) permits redistribution with attribution. This assignment app and its timestamp-reference analysis are independent of Elexon and do not imply Elexon endorsement.

## API

All application routes are read-only `GET` under `http://127.0.0.1:8000/api/v1`:

| Route | Purpose |
| --- | --- |
| `/health` | Process health only; it does not certify that data is present. |
| `/data-status` | Active or explicitly pinned snapshot, import outcome and policy status. |
| `/forecast` | Next-day forecast grid for `decision_date`, `cutoff` and optional `snapshot_id`; omits actuals and errors. |
| `/accuracy` | Retrospective rows, coverage, pooled metrics and daily results for `decision_from`, `decision_to`, `cutoff` and optional `snapshot_id`. |
| `/export` | CSV for `view=forecast` or `view=accuracy`, matching date/cutoff parameters and a required `snapshot_id`. |
| `/forecast/revisions` | Eligible forecast revisions for one target; the optional UI viewer is deferred. |

See the [API contract](docs/API_CONTRACT.md) for response fields, validation and error states. The browser calls only stored-data routes; Elexon access belongs to the import CLI.

For simple process probes, `GET http://127.0.0.1:8000/health` is an alias of `/api/v1/health`. Both return `{"status":"ok"}` and say nothing about dataset availability; use `/api/v1/data-status` to inspect stored data.

## Checks and release evidence

```bash
make check
npm --prefix frontend exec -- playwright install chromium
make test-browser
make test-ui-runtime
make benchmark-api
make audit-security
```

`make check` runs Python lint/format/tests and frontend lint/type/tests/build. By default browser tests start their own servers on ports 8000 and 5174. To keep a separately running app untouched, use `GRIDBRICKS_TEST_API_PORT=4285 GRIDBRICKS_TEST_WEB_PORT=4284 npm --prefix frontend run test:browser`; both ports can be changed. The production UI runtime check uses ports 4184/4185 and an isolated synthetic snapshot. `make benchmark-api` measures the saved default live snapshot; it needs that dataset present. Advisory checks and browser installation may need network access.

On 27 October 2026, `make check` passed 157 backend tests, 79 frontend tests, lint, type checking and the production build. The isolated Chromium suite passed 20 cases after the Docker packaging change. Nine axe scans reported no violations in their scoped page and dialog checks. The saved live snapshot returned 744/744 matched January benchmark rows in a direct API check. Earlier evidence includes a 100-request full-January API benchmark at 133.15 ms p95 on the recorded machine, under the local 1,000 ms target, and an independent [CSV reconciliation](docs/evidence/live-export-reconciliation.json) of all 744 live Accuracy rows. [Backend test report](docs/BACKEND_TEST_REPORT.md), [browser test report](docs/BROWSER_TEST_REPORT.md), [release validation](docs/RELEASE_VALIDATION.md), [UI validation](docs/UI_VALIDATION.md) and [security review](docs/SECURITY_REVIEW.md) describe methods and limits. The [client](docs/presentations/CLIENT_WALKTHROUGH.md) and [technical](docs/presentations/TECHNICAL_WALKTHROUGH.md) outlines and a combined [under-ten-minute video script](docs/presentations/ASSIGNMENT_VIDEO_SCRIPT.md) are included.

The API and import CLI write JSON-line diagnostic events to stderr. API responses carry `X-Request-ID`; match it to an `http_request` event to inspect the route, duration, outcome, validated date bounds, cutoff and resolved snapshot. Import events show each dataset window's attempts and counts, and publication or failure. Logs exclude raw URLs, query strings and source payloads.

## Assignment delivery and Vercel

The analytical application and Docker image are verified locally. The source is in the anonymous-named [public GitHub repository](https://github.com/vsuman00/r8m4q2v6). The assignment submission is **PARTIAL**: there is no Vercel deployment, recorded YouTube video or submitted form. The [assignment audit](docs/ASSIGNMENT_AUDIT.md) lists each requirement, evidence and remaining action. There is no deployment URL to link yet; add the verified production URL here after deployment.

The Vercel build uses one containerized web app. [`Dockerfile.vercel`](Dockerfile.vercel) builds the Vite frontend and locked Python backend, then serves the built frontend and `/api/v1` from one HTTP process listening on Vercel's `$PORT`. Docker builds and tests this image locally; Vercel builds the same Dockerfile for deployment. Docker Compose is not a Vercel deployment step. [Vercel's container guide](https://vercel.com/kb/guide/does-vercel-support-docker-deployments) describes the image entry point and Function behavior.

To run the assembled image locally, start Docker Desktop and run:

```bash
docker build -f Dockerfile.vercel -t gridbricks-vercel:assignment .
docker run --rm -p 127.0.0.1:4286:8000 -e PORT=8000 gridbricks-vercel:assignment
```

Open `http://127.0.0.1:4286`. The image serves the reviewed live January snapshot from `deployment/data/`; its build checks the SQLite database, manifest and all 69 saved raw-input hashes. The API opens SQLite read-only. Browser requests never import. A source refresh needs a new reviewed deployment artifact, because Vercel container instances do not provide durable local writes.

The production Host is accepted from Vercel's `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL` environment values. For a custom domain, set `GRIDBRICKS_ALLOWED_HOSTS` to a comma-separated list of bare DNS names. The local two-server development commands above still use loopback. Import the public repository root into Vercel, deploy to production, and verify Decision, Accuracy, CSV and the production URL in a signed-out browser. Update this section with that URL only after it works. The [audit](docs/ASSIGNMENT_AUDIT.md#vercel-and-docker-delivery-path) tracks the remaining release checks.

## AI-assisted development disclosure

AI tools assisted with planning, implementation, documentation and review. The source research, analytical policy, test results and deployment status are stated with their evidence and limits; AI output is not treated as independent validation.
