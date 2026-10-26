# GridBricks UI implementation handoff

Date: 26 October 2026. Design reference: [HTML mockup](../design/ui-mockup.html), [Decision preview](../design/decision-preview.png), and [Accuracy preview](../design/accuracy-preview.png).

The user has instructed us to start building from the supplied design directory. This supersedes the earlier frontend hold and authorizes this handoff and UI implementation. It does not resolve source alignment or authorize fabricated analytical results.

## Scope and visual contract

Implement both Decision and Accuracy screens in React/TypeScript. Match the supplied teal, blue-grey, white-panel design: a 198px desktop sidebar, workspace breadcrumb, historical replay badge, page heading, compact filter panel, three summary cards, chart/context grid, interval table, and source/methodology footer. Accuracy adds coverage, signed-error illustration, and daily summaries. Use system fonts, tabular numeric text, subtle borders, 12px panel radii, and no decorative hero imagery.

Reference tokens: ink `#18313e`, muted text `#586b76`, teal `#116d70`, soft teal `#e9f3f1`, borders `#dce4e7`, page `#f3f6f7`, amber `#8b5319`, amber surface `#fff5e8`. The user requires SCSS: use `frontend/src/styles.scss`, a shared Sass token module, and nested component/state rules. No Tailwind or plain application stylesheet. Runtime CSS custom properties remain available to SVG. Preserve the mockup's hierarchy while allowing labels to wrap and increasing small text where needed for readability. Illustrative SVG paths may reuse the supplied curves; they are not generated measurements.

## Current data boundary

Only `/api/v1/health` exists. This UI delivery must be complete as an interactive preview, clearly labelled throughout. Keep measured values as unavailable placeholders. Keep CSV disabled with a visible explanation until immutable snapshots and export exist. Never show an actual line, actual column, or error in Decision view. Accuracy is retrospective and its illustrations are not validated January results. Show no invented snapshot, retrieval time, coverage, revision publication, or metric.

The top strip identifies the preview and permits deliberate exploration of layout, partial, conflict, empty, loading, data-unavailable, and alignment-pending states. These controls are preview controls, not source checks. Alignment-pending blocks the Accuracy chart but leaves Decision exploration available. Error/empty/loading states must not leave a stale chart or imply zero. Missing/conflicting samples use gaps and text labels.

## Interactions

- Navigation switches Decision/Accuracy and preserves each view's applied filters. Use real keyboard-accessible buttons and `aria-current`.
- Decision defaults to 15 January; Accuracy defaults to 1-31 January; both default to 09:30 Europe/London, labelled a demo assumption. These are preview dates, not a claimed active-snapshot range.
- Form drafts apply only after validation. Restrict decisions to January 2026, require end date on or after start, and validate HH:MM cutoff. Show field-level errors. Applied delivery labels derive from the following calendar day, including 31 January to 1 February.
- Keep view, applied date/range, cutoff and preview state in the URL; support reload and browser Back/Forward. Explain and recover from invalid URL state without fetching an unsupported query.
- Applying filters updates labels and interval/date templates, announces that no source data was fetched, and resets table pagination. Do not recalculate selection, alignment or metrics in JavaScript.
- Interval templates show three rows initially, with expansion and bounded pagination for the full selected grid. Label every value as a placeholder; preview gaps/conflicts are identified explicitly. Daily template rows follow the applied range.
- Data details opens a native modal with sources, snapshot/import placeholders, policies and the local process-health check. It supports Escape, traps focus, and restores the opener. A healthy process never means data is available. Cancel stale or timed-out health requests; offer retry on failure.
- All source/methodology and data-detail buttons open the same information panel. A table link moves focus to the equivalent accessible table region. Disabled export has an accessible reason.

## Responsive and accessibility requirements

Desktop retains the reference sidebar and two-column chart/context area. At tablet widths collapse the context under the chart rather than discard information. At 680px and below use a compact header and horizontal view navigation, stack controls as needed, and wrap summary cards without truncating important labels. At 320px there must be no page-level horizontal overflow. Wide tables may scroll inside a labelled, keyboard-focusable region.

Use labelled native inputs, visible focus, a skip link, real headings, semantic tables with captions and column scopes, status announcements, non-colour gap/error labels, reduced-motion support, and 44px touch controls. Keep illustrations clearly described to assistive technology. Use no external fonts or image downloads. Preview rendering must work offline even if the local API is unavailable.

Graphs use a finite 650ms line reveal and a 500ms area/actual fade; state entrances last 180ms. No continuous chart animation or expensive layout animation. Respect `prefers-reduced-motion` by disabling motion. Bound table rendering to 24 interval templates per page and the daily table's scroll region to avoid a cluttered or slow month view.

## Verification and scope limits

Verify component/state tests, lint, TypeScript, production build and existing backend checks. Add managed-server Playwright flows for both views, form validation, URL reload/history, pagination, all preview states, keyboard/modal focus, process-health failure/retry, and narrow layouts. Run axe against both views and modal at representative widths. Inspect rendered desktop and mobile screenshots against the provided references. Record measured build size and browser timing as local UI evidence, without treating them as the future API's NFR02 benchmark.

This section records the original UI-first handoff. The user later required the full application and asked to remove the interactive mockup preview. They also removed the top snapshot strip and breadcrumb/review badge because those elements repeated information shown in the actual workflow. Decision and Accuracy now use stored analytical API responses only; source identity and the retrospective caveat remain in contextual content and Data details. The original HTML and images remain design references; current verification is in [browser test report](BROWSER_TEST_REPORT.md) and [release validation](RELEASE_VALIDATION.md).

The full application security review now covers the import CLI, snapshot storage, analytical routes, CSV and browser as well as the original process-health route. See [security review](SECURITY_REVIEW.md). Authentication and public hosting require a separate decision.
