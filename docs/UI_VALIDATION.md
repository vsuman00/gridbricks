# UI delivery validation

Date: 26 October 2026. Current result: the real-data UI passed the browser and production-runtime checks. The user retired the interactive mockup preview after the earlier checks in this file. The [current browser report](BROWSER_TEST_REPORT.md) records the replacement tests and live browser walkthrough; historical preview counts below are retained as dated evidence only.

## Current real-data UI after preview removal

### Single-container check, 27 October 2026

The reviewed live-snapshot Docker image served the built UI and `/api/v1` from one loopback port. A real Chromium run opened Decision and Accuracy, waited for the stored interval tables, and observed no page errors. It also found the Elexon attribution and licence link in the live-data footer at mobile width. The container's UI and asset responses had a self-only CSP; API responses retained their restrictive JSON CSP. A separate isolated browser suite passed all 20 cases after the packaging change. This is local container evidence, not a Vercel production test.

The running app has Decision and Accuracy views backed by pinned API responses. `mode=preview` shows an unsupported-link warning and makes no data request until reset. The user also removed the redundant top snapshot strip and breadcrumb/badge row. Source identity remains in the context and Data details. After the cutoff-note follow-up below, `make check-frontend` passed 79 tests, lint, TypeScript and build. The isolated Chromium suite passed 20 real-data cases, including eight view/width axe scans and one settled-dialog scan with no reported violations. `make test-ui-runtime` passed eight production cases. [Live Decision](evidence/ui/real-decision-gpt-browser.png) and [Accuracy](evidence/ui/real-accuracy-gpt-browser.png) screenshots show the simplified layout before the copy follow-up; the later live inspection is recorded below.

### Additional UI audit, 26 October 2026

Fresh `make check-frontend`, isolated Chromium tests on ports 4284/4285, and `make test-ui-runtime` passed: 78 frontend tests, 19 browser cases, and eight runtime cases. The default browser-test port 8000 was already occupied by the running application, so the isolated ports were used. A live Accuracy view was also inspected in the in-app browser; it showed no console errors or warnings during that check.

**PARTIAL, copy follow-up:** With the saved live snapshot and `cutoff=09:00`, the filter, export URL, and recalculated metrics reflect 09:00, but the scope note still reads “09:30 is a configurable demo assumption.” The same fixed note appears during loading. The hard-coded text is in `frontend/src/components/DataOverview.tsx` and `frontend/src/components/DataLoading.tsx`. This can make the active cutoff unclear even though the analysis uses the requested time. Show the selected cutoff alongside the 09:30 demo default, then add a non-default cutoff browser assertion. No code was changed in this audit.

### Cutoff-note follow-up, 26 October 2026

**VERIFIED:** The loading state now labels the applied filter cutoff, and the loaded state labels the cutoff returned with the analysis. Both use the same `ScopeNote` component and name 09:30 UK as the demo default. A unit test covers loading and loaded 09:00 labels; a Chromium case applies 09:00, then checks the note and pinned CSV URL. `make check-frontend` passed 79 tests, lint, type checking and build; the isolated browser suite passed 20 cases; `make test-ui-runtime` passed eight cases. The live 09:00 Accuracy view showed the revised note beside recalculated metrics, with no console errors or warnings. This closes the copy issue above. The checks remain local Chromium and scoped accessibility evidence, not a multi-browser certification.

## Earlier integrated verification

At this earlier checkpoint, Decision and Accuracy read a pinned snapshot through FastAPI, while `mode=preview` still exposed labelled illustrations. The live January desktop/mobile screenshots were opened and inspected after data integration: [Decision 1440px](evidence/ui/live-decision-1440.png), [Decision 320px](evidence/ui/live-decision-320.png), [Accuracy 1440px](evidence/ui/live-accuracy-1440.png), and [Accuracy 320px](evidence/ui/live-accuracy-320.png). No page-level horizontal overflow was observed in those captures. The preview route has since been removed.

`make test-browser` passed 35 Chromium cases: 15 stored-fixture workflows and responsive checks, plus 20 explicit preview cases. Stored-data flows verify eligible vintage selection, no actual leakage into Decision, retrospective metrics and policy note, stale-response ordering, unknown snapshot recovery, API/no-dataset distinction, pinned CSV download, URL reload, and both views at 320/768/1024/1440px. The suite ran 24 axe scans across stored-data and preview page/modal states with no reported violations. This is an accessibility smoke check, not complete WCAG certification or a multi-browser test.

`make test-ui-runtime` passed eight production view/width cases against an isolated synthetic snapshot and a real local API. [The runtime artifact](evidence/ui/production-runtime.json) records strict self-only CSP and inline-script blocking, zero external assets, no page overflow or browser errors, finite graph motion, maximum measured CLS 0.000295, maximum frame-gap p95 16.8 ms, and 83,811-byte gzipped JavaScript plus 4,964-byte gzipped SCSS output. These are short local M4 measurements, not field performance guarantees. The separate [full-January API benchmark](evidence/api-benchmark.json) supplies the analytical response measurement.

The live screenshots show the 09:30 January snapshot; fixture browser tests show deliberate gaps/conflicts. Neither screenshot is proof of WINDFOR's physical averaging interval or final settlement truth. The [release record](RELEASE_VALIDATION.md) links source, CSV, and security evidence.

## Historical preview-phase evidence

## Scope and visual evidence

The reference is [design/ui-mockup.html](../design/ui-mockup.html), with its original Decision and Accuracy PNG previews. The user instructed implementation from these references, lifting the earlier frontend hold. [UI_DESIGN.md](UI_DESIGN.md) was written before frontend delegation. The original design files and empty historical placeholder were preserved.

The rendered UI retains the teal/blue-grey palette, workspace sidebar/navigation, filter panel, summary cards, chart/context area, interval table and methodology footer. Accuracy adds retrospective coverage, signed-error illustration and daily template rows. At tablet and mobile widths the context stacks instead of disappearing, controls wrap, and wide tables scroll inside labelled regions.

The manager inspected rendered desktop and mobile images against the supplied reference. Final screenshots after the SCSS conversion:

- [Decision, desktop 1440px](evidence/ui/decision-1440.png)
- [Accuracy, desktop 1440px](evidence/ui/accuracy-1440.png)
- [Decision, mobile 320px](evidence/ui/decision-320.png)
- [Accuracy, mobile 320px](evidence/ui/accuracy-320.png)

These screenshots are UI evidence, not observed wind data or measured forecast performance. The reference's curves were retained as clearly labelled schematics; measured values, snapshot and retrieval details remain unavailable. Decision view exposes no actual or error series. CSV is disabled with a visible explanation.

## Requirement-to-evidence audit

| Requirement | Implemented behavior | Verification |
| --- | --- | --- |
| Follow both supplied mockups | Reference hierarchy, colours, panels, charts and template tables implemented in React | Written handoff, independent component review, rendered screenshot comparison |
| Responsive UI | Both views at 320/768/1024/1440px; context retained; bounded table scrolling | Eight browser viewport cases; no page-level horizontal overflow; screenshots |
| SCSS styling | `styles.scss` uses a shared Sass token module and nested component/state rules; no application CSS source or Tailwind | Entrypoint/source inspection, pinned Sass, clean setup/build; normalized compiled output matched the previous visual rules |
| Smooth graph motion | 650ms line reveal, 500ms area/actual fade, 180ms state entrance; no continuing animation | Browser animation/reduced-motion checks and eight production runtime samples |
| Fast, uncluttered rendering | No external fonts/assets, small static SVG illustrations, interval pagination capped at 24 rows, bounded daily table | Production bundle budgets, resource/overflow/layout-shift checks and sampled frame timing |
| Valid filters and delivery labels | Drafts apply only after January/date-range/HH:MM validation; 31 January derives 1 February delivery | Unit/component/browser tests, first-error focus and unapplied-change message |
| Shareable navigation | Applied view/date/range/cutoff/preview state in URL; safe invalid-link recovery; Back/Forward and reload | Parser/serialization tests and browser navigation/XSS-input cases |
| Complete preview states | Layout, partial, conflict, empty, loading, unavailable and alignment-pending illustrations; stale chart removed in blocked states | Both-view browser state flows; explicit missing/conflict labels and gap schematic |
| Keyboard and accessibility | Skip/table links, labels, native modal with explicit Tab wrap, Escape/opener restoration, semantic tables and status text | Keyboard browser walkthrough and 16 axe scans across both views/four widths/page+modal |
| API failure handling | Modal-only process check, abort/timeout/late-response guards and retry; preview usable offline | Hook tests for timeout/stale response; real local API smoke and browser failure/retry flows |
| Clean code and reproducible setup | Focused typed components/hooks, locked dependencies and disabled npm dependency scripts | `make setup`, `make check`, independent review; no lint/type/build failures |
| Secure implemented backend | Trusted local Host, bounded raw queries, exact CORS, read-only surface, safe headers and generic errors | 21 source-aware and 21 real-server black-box cases plus seven original health tests; [security review](SECURITY_REVIEW.md) |
| Frontend and dependency security | Safe URL handling/React text rendering, production CSP and safe document headers, advisory/signature checks | Invalid-URL script probe, production inline-script rejection, npm/uv audits and npm signature report |

## Test and build results

Environment: macOS arm64 on Apple M4, Node 26.5.0, npm 11.17.0, Python 3.12.12, uv 0.11.8, and Chromium managed by pinned Playwright 1.64.1. Other supported runtime versions and browsers were not exercised here.

| Command or check | Result |
| --- | --- |
| `make setup` | Locked backend sync and clean npm install passed; npm dependency scripts disabled |
| `make check` | Backend lint/format, 49 backend tests, frontend lint/type checking, 28 frontend tests and production build passed |
| `npm --prefix frontend run test:browser` (`make test-browser`) | 20 passed, zero unexpected/flaky/skipped results after SCSS conversion |
| axe with WCAG 2 A/AA and 2.1 A/AA tags | 16 page/modal scans, zero reported violations |
| `node frontend/scripts/verify-runtime.mjs` | Eight production UI cases passed; safe headers/CSP and inline-script blocking passed |
| `backend/.venv/bin/ruff check --select S backend/src` | Passed static security rules |
| `uv audit --project backend --locked --python-version 3.12 --python-platform aarch64-apple-darwin` | No known vulnerabilities or adverse statuses reported in 25 selected packages |
| `npm --prefix frontend audit --json` | Zero known vulnerabilities in the checked npm graph, including development dependencies |
| `npm --prefix frontend audit signatures --json` | Exit 0; no invalid/missing entries reported |

The browser suite found a native modal focus-wrap gap. An explicit bounded Tab handler was added, then repeated forward/reverse Tab, Escape and opener restoration passed. Backend security tests also ran before hardening and observed failing checks before the fixes. Independent frontend/test/backend agents reported their results to the manager; the manager reviewed the resulting source, evidence and rendered UI.

[Machine-readable summary](evidence/ui/verification-summary.json) retains browser case results and hashes of relevant final files. Full transient browser output is `frontend/test-results/ui-results.json`; traces/screenshots are retained on failure. [Backend evidence](evidence/security-backend-review.json) preserves security command outcomes and backend hashes.

## Local production UI measurements

[Production runtime evidence](evidence/ui/production-runtime.json) records a static build served on loopback with production CSP, separately from [development navigation timing](evidence/ui/local-ui-timing.json). On the recorded host, the eight production cases had:

- Document readiness of 23.7-43.7ms.
- Frame-gap p95 of 16.7-16.8ms during the initial animation sample.
- Zero measured initial layout shift, reported long tasks, external asset requests or browser errors.
- Zero ongoing animations after the finite entrance period.
- Main JavaScript 250,546 bytes / 76,360 gzip bytes and styles 17,726 bytes / 4,569 gzip bytes using the runtime check's gzip settings. Both are below its 100KB JS and 10KB styles gzip budgets.

These are short local Chromium samples, not universal frame-rate guarantees, field web vitals or the future NFR02 analytical API benchmark. Production headers are verified on Vite's local preview server; any eventual hosting platform must configure and verify equivalent headers.

## Security scope and limitations

The backend [security review](SECURITY_REVIEW.md) maps its implemented trust boundaries and records white-box/source-aware checks, real-Uvicorn black-box HTTP probes, static rules and dependency audit results. The frontend adds a strict production document CSP without inline/eval scripts, safe URL recovery and bounded URL input; no user input is injected as HTML. A targeted source scan found no execution/HTML-injection or credential sink in the application source.

The npm install-script policy prevents dependency lifecycle scripts from executing. The only flagged lifecycle-script package in the initial lock inspection was optional `fsevents`; no blanket exception was added. Advisory/signature checks have finite coverage and do not establish that every package is benign. The Python advisory check excludes the isolated build-tool environment. No Git history exists to scan for historical secrets.

No authentication, accounts, database, source-import endpoint, analytics service, snapshot export or public deployment exists yet. Their authorization, storage isolation, SSRF, CSV formula handling and reproducibility/failure controls cannot be validated before those features are built. The local HTTP demo has no TLS/HSTS or volumetric abuse-resistance claim. No exhaustive fuzzing, full penetration certification, complete accessibility conformance or absence-of-all-defects claim is made.

## Reproduce and resume

```bash
make setup
make check
npm --prefix frontend exec -- playwright install chromium
make test-browser
make test-ui-runtime
make audit-security
```

Browser tests manage backend port 8000 and frontend port 5174; stop a separately running backend first. The runtime check owns port 4184 and cleans it up. The ordinary UI can run separately at 5173. Audits and first-time tool/browser installation require internet; application fixture/state tests and the built UI do not download Elexon data.

The user-requested UI delivery is complete. T02 is VERIFIED. T05/T09/T11 remain PARTIAL until real forecast/accuracy APIs, immutable snapshots, publication/actual provenance, export parity and analytical response ordering are verified. Next work is T03 one-day ingestion alongside T01 source semantics research. The unresolved interval-meaning question still prevents T06 alignment. No full-assignment release, client approval, Git publication or deployment is inferred from these UI checks.
