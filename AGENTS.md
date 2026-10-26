# Project instructions for agents

## Start here

This project is a React and Python assignment for reviewing Elexon wind forecasts available before a day-ahead buying decision and evaluating them against wind outturn. Follow the governing documents before implementing a feature.

Read [README.md](README.md), [todo.md](todo.md), and [memory.md](memory.md) for orientation, then the relevant sections of:

- [PRD](docs/PRD.md): scope, requirements, assumptions, and acceptance criteria.
- [Architecture](docs/ARCHITECTURE.md): processing rules, data model, APIs, and component boundaries.
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md): T01-T12, dependencies, and verification.
- [Source research](docs/SOURCE_RESEARCH.md) and [ADR-001](docs/decisions/0001-mvp-baseline.md): evidence, open questions, and proposed decisions.

Explicit user instructions take precedence over project defaults, subject to system and developer instructions. The PRD governs product scope, architecture governs technical contracts, and the plan governs sequencing. The todo file tracks progress; project memory is a summary, not a substitute for source documents or current evidence. Surface material conflicts and resolve them before dependent work. Proceed with independent authorized work while a conflict is unresolved.

## Work in small, verifiable steps

1. Inspect existing files and Git state when available. Preserve user changes and unrelated work.
2. Select the next task whose dependencies are satisfied. Implement the smallest useful slice with its acceptance checks.
3. Use the documented defaults where the client has not supplied a decision. Keep assumptions visible; do not invent approval or add a routine permission gate.
4. Verify behavior with appropriate tests and inspect the resulting UI when changing user interactions.
5. Update [todo.md](todo.md) with status, evidence, and the next step. Keep the project-local [memory.md](memory.md) current with verified facts and unresolved decisions as part of authorized project work. This does not authorize changing global agent memory.
6. Report what changed, what was verified, and any remaining limitation. A documentation change does not authorize starting implementation when the user requested only documentation.

Use `PLANNED`, `IN PROGRESS`, `IMPLEMENTED`, `VERIFIED`, `PARTIAL`, `BLOCKED`, and `DEFERRED` consistently. Check a task off only after its acceptance criteria and required verification pass. Record the reason and affected dependency for a blocked task. Do not describe fixture tests as live-provider validation or a local demo as a production deployment.

## Preserve the analytical contract

- Use only WINDFOR and FUELHH records with `fuelType = WIND` as analytical inputs. Other sources may explain definitions; they do not expand the input scope.
- The current assumption is decisions on 1-31 January 2026 and delivery on 2 January-1 February. The default cutoff is 09:30 `Europe/London`, configurable and labelled as a demo assumption.
- Store timestamps in UTC; construct market dates and cutoffs in `Europe/London`. Distinguish target, publication, cutoff, and retrieval timestamps.
- Select the greatest `publishTime <= cutoff` separately for each target. Keep older eligible publications and all revisions. Never select a later revision through a latest-now shortcut.
- Exact duplicates may be deduplicated. A conflicting newest eligible publication must remain unresolved; do not choose by row order or silently fall back.
- Verify WINDFOR's physical interval meaning before implementing the proposed hourly-average alignment. Hourly timestamps alone do not prove hourly averages. This dependency affects T06, while setup and forecast exploration may proceed.
- Keep missing data as gaps with reason counts. Zero generation is a real value. Do not interpolate, forward-fill, or duplicate forecasts to inflate the sample count.
- Define error as forecast minus actual. Use pooled matched intervals for MAE, RMSE, and bias. Return null metrics when there are no matched observations; show expected and matched counts.
- Keep each response and export tied to one immutable snapshot and named policies. Retain raw source provenance, actual revisions, and constituent actual records.
- Historical accuracy is retrospective. Do not expose future actuals or whole-month error statistics as knowledge available at an earlier buying decision.
- Keep MW and MWh distinct. Energy summaries, purchase recommendations, financial savings, new forecasts, and additional data feeds are outside the current v1 scope.

## Implementation and verification

Follow the proposed React/TypeScript frontend, FastAPI backend, SQLite storage, and separate import CLI unless an explicit decision changes that design. Keep selection, alignment, and metrics in Python. Browser requests read stored snapshots and must not trigger Elexon downloads.

Treat commands in the plan as planned interfaces until their owning task creates them. Inspect the actual Makefile, package scripts, and test files before running or claiming a command exists. Pin compatible dependencies during T02; installed runtime versions are not proof of package compatibility.

Prioritize meaningful checks for cutoff boundaries, revision conflicts, missing constituents, actual selection, month boundaries, equations, snapshot immutability, CSV parity, failed imports, and frontend response ordering. Use deterministic fixtures for automated checks and label synthetic data. Record live-source outcomes separately.

Before claiming completion, match the task's acceptance criteria to actual evidence. Update governing documents and the ADR if an authorized change alters scope, semantics, or contracts. Keep secrets and client data out of source, logs, fixtures, and memory. Keep Git actions and publication within the user's authorized scope; preserve unrelated changes.

## UI design and styling

The user first requested a designer-led mockup review and then explicitly instructed implementation from the supplied design directory. The earlier frontend hold is lifted. [UI_DESIGN.md](docs/UI_DESIGN.md) is the written handoff, using [DRAFT 01](design/ui-mockup.html) and its saved Decision/Accuracy images as the visual reference. The existing empty [DesignPlaceholder.tsx](frontend/src/DesignPlaceholder.tsx) is preserved as a historical placeholder.

Use SCSS for application styling, with shared Sass tokens and component/state nesting. Do not introduce Tailwind or a plain application CSS source file. Keep graphs responsive and animations finite, smooth, and disabled by reduced-motion preferences. Read the handoff and governing PRD before frontend changes.

The UI reads stored forecasts and retrospective comparisons from the API. The user later requested removal of the interactive mockup preview; the original design file remains a reference only. Preserve the local read-only API boundary and record black-box, source-aware, dependency and browser security evidence with its limits in [SECURITY_REVIEW.md](docs/SECURITY_REVIEW.md) and [UI validation](docs/UI_VALIDATION.md). Do not invent an approval gate for work already authorized.

## Text watermark cleaning preference

For every task that creates or edits user-facing prose, apply the installed `clean-user-facing-text` skill before delivering the text. This is the preferred self-contained prose workflow and does not require an HTTP service or external model backend. Preserve meaning, factual claims, citations, links, code, and quoted material.

Use the installed `remove-ai-marks` skill for service-based inspection and cleaning of supported files or explicitly requested provenance removal. Its local service is at `http://127.0.0.1:8765`, installed in `~/.codex/tools/watermarks-remover` and started at login by the user's LaunchAgent. Follow the skill's service health and capability checks. Plain-text statistical rewriting through `/clean` requires a separately configured rewrite backend; use the self-contained prose workflow unless that backend has been configured.

Report clearly when requested cleaning cannot run. Never claim that a watermark was removed or that text is undetectably human-written without evidence. An unavailable service must not prevent completion of unrelated work.
