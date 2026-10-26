# Browser test report

Date: 26 October 2026. Target: the local GridBricks React/SCSS frontend and FastAPI backend. I tested the saved live January snapshot in the ChatGPT in-app browser, then ran isolated Chromium checks against the synthetic fixture. The user requested removal of the interactive mockup preview during this review, so the final checks cover the real-data frontend only.

## Result

The later [cutoff-note follow-up](UI_VALIDATION.md#cutoff-note-follow-up-26-october-2026) passed 79 frontend tests and 20 Chromium cases, plus eight production runtime cases. The live 09:00 Accuracy view was inspected after that UI change. The details below record the earlier preview-removal checkpoint.

**Pass for the tested local workflows.** At that checkpoint, the real-data browser suite passed 19 of 19 Chromium cases. Frontend lint, type checking, production build and 78 unit/component tests passed. Backend lint/format and 151 tests passed. The production UI runtime check passed eight cases. Nine scoped axe scans reported no violations. The Python and npm dependency audits reported no known vulnerabilities in their selected graphs.

The app was initially visible from the browser cache while both local servers were stopped. Changing a filter then showed the expected “Data request failed” state. I started `make backend-dev` and `make frontend-dev`, reloaded, and completed the live walkthrough. This was a local process availability issue; it did not alter the saved snapshot.

## Live browser walkthrough

| Area | Check | Result |
| --- | --- | --- |
| Startup | React page and stored snapshot load after both servers start | Pass |
| Decision | 15 January date, 09:00 cutoff selects 7,398 MW at 16 January 00:00 from a 07:30 publication; 09:30 selects 7,472 MW from the 09:30 revision | Pass |
| Decision separation | Forecast view shows selected values, coverage and publication lineage without actual or error columns | Pass |
| Intervals and lineage | Expanded all 24 intervals and a source-record disclosure; response row, retrieval time, hash and request were visible | Pass |
| Accuracy | Full January showed 744/744 matched, MAE 1,995.57 MW, RMSE 2,498.82 MW and bias +1,727.98 MW | Pass |
| Date range | One-day 15 January Accuracy showed 24/24 matched, MAE 897.33 MW, RMSE 1,124.31 MW and bias +393.5 MW | Pass |
| Validation | Reversed date range kept the applied result and displayed a field error | Pass |
| Methodology | Data details showed the pinned snapshot, WINDFOR/FUELHH sources, named policies, import outcome and local API status | Pass |
| Provenance | Accuracy row disclosed both forecast and actual constituent records and the temporal-reference flag | Pass |
| Export | Accuracy export link used the current date, cutoff and snapshot; the local HTTP response was CSV with a download filename | Pass |
| History | Back navigation restored a previous applied view and filters | Pass |
| Mockup removal | The running UI no longer has an “Open UI preview” control; an old `mode=preview` URL gives an unsupported-link warning and Reset returns to stored data | Pass |

The current live screenshots are [Decision](evidence/ui/real-decision-gpt-browser.png) and [Accuracy](evidence/ui/real-accuracy-gpt-browser.png). They show the finished workspace without the mockup switch, the redundant snapshot strip, or the extra header row. Source mode and snapshot identity remain in the context card and Data details. The original design files remain under `design/` as references.

## Automated browser and runtime coverage

The 19-case Chromium run used isolated ports 4284/4285 and the generated synthetic fixture. It checked cutoff vintage selection, conflict/gap handling, absence of future actuals in Decision, API metric labels, stale response ordering, missing dataset versus failed API, unknown snapshot recovery, CSV download and row parity, URL reload/history, validation, source details, keyboard links and modal behavior. Both views passed responsive and axe checks at 320, 768, 1024 and 1440 pixels. A settled data-details dialog passed a ninth axe scan. Chart animation was finite and disabled under reduced-motion preference.

The production UI check ran eight view/width cases against an isolated fixture API. It checked document headers and CSP, no external assets or browser errors, no page-level horizontal overflow, finite motion and local layout timing. The browser suite used the app's fixture to exercise missing and conflicting data; those states were not observed in the saved live January snapshot.

## Findings and limits

- **Resolved:** The mockup switch and preview route were irrelevant to the finished frontend. Preview-only React components, controls, URL state and tests were removed. The HTML mockup remains a design reference.
- **Resolved:** The top snapshot strip and “Retrospective review” badge repeated information available in the page and Data details. Both were removed, along with the redundant breadcrumb row. Accuracy now states in plain language that it compares cutoff-selected forecasts with later wind generation. The contextual retrospective note remains beside the chart.
- **Resolved test issue:** A new modal axe scan initially ran during its 180 ms entrance fade, producing transient contrast findings. Waiting for the dialog animation to finish made the same scan pass. A broad text locator in another new test was narrowed. The final full suite passed.
- **Operational:** The app needs both local servers running. A cached page alone does not show that the backend is available. The failure state and recovery were observed in the in-app browser.
- **Scope:** The in-app browser walkthrough used one live snapshot and one desktop viewport. The automated suite used Chromium and synthetic fixtures for edge states and widths. This is not a multi-browser certification, full accessibility audit, exhaustive penetration test, live Elexon reimport, or proof that every defect is absent. The physical averaging meaning of WINDFOR remains unverified; the Accuracy view labels its timestamp-matched benchmark accordingly.

## Reproduce

Start the app with `make backend-dev` and `make frontend-dev` in separate terminals, then open `http://127.0.0.1:5173`. Run the checks without taking over those ports:

```bash
make check-frontend
make check-backend
GRIDBRICKS_TEST_API_PORT=4285 GRIDBRICKS_TEST_WEB_PORT=4284 npm --prefix frontend run test:browser
make test-ui-runtime
make audit-security
```

The transient Playwright JSON output is `frontend/test-results/ui-results.json`. The [UI validation](UI_VALIDATION.md), [release validation](RELEASE_VALIDATION.md) and [security review](SECURITY_REVIEW.md) give the broader evidence and limits.
