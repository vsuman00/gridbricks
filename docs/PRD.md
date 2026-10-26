# Product requirements: wind forecast decision support

Version: 0.1. Date: 26 October 2026. Status: implemented local analytical application under release verification. The adopted timestamp-reference benchmark and its physical limitation are documented in [ADR-002](decisions/0002-timestamp-matched-reference.md). The user authorized the full application from the supplied mockups with SCSS, responsive motion, and scoped security testing; see [todo](../todo.md) for task evidence.

## 1. Purpose and product boundary

Give a UK utility's day-ahead procurement team a clear view of the Elexon national wind forecast published by its decision deadline, then quantify how that forecast compared with reported outturn.

The product answers:

1. What wind forecast was available for tomorrow when the team had to decide?
2. How large and in which direction were errors for forecasts selected using that same deadline?

This assignment supplies national wind forecasts and actuals only. It does not supply customer demand, contracted positions, portfolio allocation, prices, or other renewable generation. The application must not turn national wind output into a client purchase quantity or claim financial savings. Actuals are the supplied FUELHH outturn reference, not a promise of final settlement truth. Source coverage is narrower than every wind turbine in the UK; use the source limitations in [research](SOURCE_RESEARCH.md).

## 2. Users and workflows

| User | Need | Workflow |
| --- | --- | --- |
| Procurement analyst | Inspect the forecast known by a buying deadline | Choose decision date and cutoff, review next-day profile, inspect selected publications, export |
| Analyst reviewing performance | Quantify historical forecast error | Choose a decision-date range and cutoff, compare forecasts with outturn, inspect coverage and daily errors |
| Technical reviewer | Reproduce and assess results | Inspect saved inputs, snapshot identity, selection policy, alignment policy, and automated checks |

Client demonstration uses historical replay. January 2026 is in the past; a refreshed download does not make this a live trading screen.

## 3. Scope and assumptions

| ID | Rule | Status |
| --- | --- | --- |
| A01 | Decision dates are 2026-01-01 through 2026-01-31, inclusive | Proposed interpretation of the brief |
| A02 | Each decision covers the following Europe/London calendar day: delivery dates 2026-01-02 through 2026-02-01 | Consequence of A01 |
| A03 | Default cutoff is 09:30 Europe/London; analysts may change it | Proposed demo default; client deadline unknown |
| A04 | Forecasts with publishTime equal to the cutoff are eligible | Proposed application boundary rule |
| A05 | All analytical input comes from Elexon WINDFOR and FUELHH WIND | Assignment requirement |
| A06 | Forecast selection is per target interval, so one displayed day may contain different publication times | Proposed selection policy |
| A07 | Retrospective actuals use the latest unambiguous publication present in a pinned dataset snapshot | Proposed reproducibility policy |
| A08 | Compare each hourly forecast target once with the exact-time FUELHH half-hour reference under `timestamp_matched_halfhour_reference_v1` | Adopted application benchmark; physical averaging equivalence remains unverified; [ADR-002](decisions/0002-timestamp-matched-reference.md) |

If the assessor intended January delivery dates, revise A01/A02 and the shared configuration before backfill. Do not silently mix decision-date and delivery-date filters. A missing client cutoff does not stop documentation or setup; the demo assumption stays visible.

## 4. Functional requirements

### Decision view

| ID | Priority | Requirement and acceptance |
| --- | --- | --- |
| FR01 | Must | Allow a January decision date and local cutoff; derive and display the next delivery date and timezone. Invalid dates and malformed cutoffs receive field-level errors. |
| FR02 | Must | For every expected target interval, select the greatest publishTime no later than the cutoff. Include older eligible publications. Changing the cutoff recomputes the whole response. |
| FR03 | Must | Display the forecast in MW, publication timestamp for each point, age at cutoff, and forecast lead time to target. Do not imply the day is one forecast vintage. |
| FR04 | Must | Show missing and conflicting intervals as gaps, with reason counts and an accessible table. Never substitute zero or a post-cutoff forecast. |
| FR05 | Should | Let the user inspect earlier eligible revisions for a selected target. Later revisions are excluded from the decision screen; an accuracy-screen comparison must label them as post-cutoff. |

### Accuracy view

| ID | Priority | Requirement and acceptance |
| --- | --- | --- |
| FR06 | Must | For each decision date in a range, apply that date's own cutoff, align selected forecasts with actuals, and display forecast and outturn together. |
| FR07 | Must | Report MAE, RMSE, signed bias, sample count, and coverage using the same matched records as the chart and export. Show definitions and units. |
| FR08 | Must | Show signed interval errors and daily breakdowns. Whole-range metrics use pooled intervals, not an unweighted mean of daily metrics. |
| FR09 | Must | Label this view retrospective. Do not show full-month errors or future actuals as information available at an earlier decision. No historical recommendation or uncertainty band is part of v1. |
| FR10 | Should | Add p90 absolute error and delivery-time-of-day breakdowns, with group sample counts. Describe p90 as an empirical statistic, not a calibrated forecast interval. |

### Trust, export, and delivery

| ID | Priority | Requirement and acceptance |
| --- | --- | --- |
| FR11 | Must | Expose dataset snapshot, retrieval time, covered decision/delivery dates, source, policies, completeness, and last import outcome. Clearly distinguish source publication time, simulated cutoff, and retrieval time. |
| FR12 | Must | Export the selected interval grid to CSV, including missing rows, selected publications, actual publication provenance, errors, units, cutoff, snapshot, and policy versions. Export and screen values must agree before display rounding. |
| FR13 | Must | Support a repeatable historical import and offline demonstration from locally saved, versioned inputs. Browser reads must not trigger source ingestion. |
| FR14 | Must | Provide explicit loading, empty, partial, conflict, source-failure, and unsupported-alignment states. Preserve the previous valid snapshot if refresh fails. |

## 5. Analytical contract

Let C(d) be the configured local cutoff converted to UTC for decision date d. Let T(d) be target intervals in the next local calendar day. For each t in T(d), select the record with maximal publishTime satisfying publishTime <= C(d), using all eligible history in the snapshot.

A same-key conflict means different generation values for the same target and publication. It is ambiguous; exclude that publication and conservatively leave the affected selected interval unresolved if it is the newest eligible publication. Do not quietly choose a value or fall back to an older vintage. Exact duplicates are harmless and deduplicated.

Source cadence and physical interval meaning are different questions. [ADR-002](decisions/0002-timestamp-matched-reference.md) adopts an explicit timestamp-matched benchmark: for each WINDFOR target t, compare once with the FUELHH WIND half-hour average starting at t. The adjacent half-hour is retained in storage but does not enter this comparison. No hourly-average or instantaneous-actual equivalence is claimed. Every accuracy response, screen and export labels this reference policy and its limitation, with `temporal_reference_mismatch` on comparison rows. Missing/conflicting exact-time actuals remain gaps even when adjacent values exist. Unknown/unsupported policy versions return unavailable accuracy. An hourly-average policy remains unsupported unless future primary evidence establishes it. Energy summaries are deferred from v1.

For matched pairs, e_i = F_i - A_i and n is the number of matched forecast intervals:

| Metric | Definition | Meaning |
| --- | --- | --- |
| MAE | sum(abs(e_i)) / n | Average absolute miss, MW |
| RMSE | sqrt(sum(e_i^2) / n) | Error measure more sensitive to large misses, MW |
| Bias | sum(e_i) / n | Positive means overforecast wind; negative means underforecast wind, MW |
| p90 absolute error | Empirical 0.9 quantile using linear interpolation | Larger historical misses, MW; should-have feature |
| Coverage | matched_count / expected_count | Completeness of the requested target grid |

Show forecast coverage and actual completeness separately. Classify unmatched rows using mutually exclusive primary reasons and retain detailed flags. With n=0, metrics are null and the UI says unavailable; with n=1, show the sample count and a limited-sample note. Do not use a headline percentage accuracy or MAPE. Compare inputs at full precision and round only for presentation.

January's adopted timestamp benchmark expects 31 x 24 = 744 hourly target comparisons and 744 exact-time reference half-hours. Ingestion retains all 1,488 delivery half-hours and available revisions. These are expected counts, not observed completeness. Never divide only by available rows or count one hourly forecast as two independent predictions.

## 6. UX and nonfunctional requirements

| ID | Proposed target | Acceptance method |
| --- | --- | --- |
| NFR01 | Controls, charts, and tables usable by keyboard; error sign communicated with text as well as color | Keyboard walkthrough, labelled controls, table access, automated accessibility smoke check |
| NFR02 | Normal January-range responses p95 <= 1 second from local storage | 100 sequential warm requests on a recorded machine and snapshot; source download time excluded |
| NFR03 | Identical snapshot, query, and policy version produce identical selected rows and metrics | Fixture-based repeatability test |
| NFR04 | Source timeout or invalid payload cannot replace the active valid snapshot | Injected failure and atomic-publication test |
| NFR05 | Read-only browser API with validated inputs, bounded January ranges, and explicit CORS configuration | API validation and header checks |

These are acceptance targets, not measured performance or a claim of full accessibility compliance. The application baseline has been validated locally. The attached assignment also requires Docker use, a public Vercel deployment, a public anonymous GitHub repository and a video submission; these delivery requirements remain separate from the locally verified analytical acceptance. Public multi-user hosting, authentication and production availability commitments require later scope.

## 7. Out of scope

- New ML forecasts, weather feeds, or substitution of other Elexon datasets.
- Client demand, purchase recommendations, thermal dispatch, price forecasts, P&L, or claimed savings.
- Automated trading, exchange integration, accounts, notifications, streaming infrastructure, and continuous live ingestion.
- Probabilistic forecasts, guaranteed error bounds, and portfolio-specific risk recommendations.
- MW-to-MWh summaries until interval semantics and duration handling are validated; v1 stays in MW.

## 8. Release acceptance and presentation

Release requires all Must requirements and the named comparison rule applied consistently. The accepted timestamp benchmark resolves the application rule while retaining its explicit temporal limitation; release must not claim hourly-average physical accuracy. Unsupported snapshot policy versions must expose unavailable accuracy. If any Must feature or required validation is incomplete, label delivery partial.

Demonstrate: choose a real January decision, inspect the eligible forecast and publication age, change the cutoff, show how selected inputs change where revisions exist, then inspect retrospective error and coverage. Verify exported rows reproduce the displayed results. No synthetic benchmark or error score may be presented as a measured January result.

Provide a client presentation explaining the workflow and limitations, plus a technical walkthrough of the architecture, selection boundaries, tests, and source evidence. [Implementation tasks](IMPLEMENTATION_PLAN.md) define the release checks.
