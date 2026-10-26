# ADR-001: Local, reproducible wind forecast replay

Status: Proposed. Date: 26 October 2026. Scope: assignment version one.

Adoption note, 26 October 2026: the user authorized implementation. T02 adopts the Python/React foundation and an installable `backend/src/gridbricks` package, with locks and backend health checks. The wider storage/analytics design remains proposed. Frontend/UI/UX is now on user-requested hold pending a design identifier. [T01 findings](../T01_SOURCE_CONTRACT.md) retain the unresolved interval-average question; no comparison policy has been activated or client approval inferred.

Later implementation update: the user instructed us to build the UI from `design/ui-mockup.html` and its previews, lifting the earlier hold. [UI_DESIGN.md](../UI_DESIGN.md) is now the handoff. Both views are implemented as an interactive preview with SCSS tokens, bounded table rendering and reduced-motion-aware animations. Synthetic curves and unavailable metrics remain explicit until the pipeline exists. Source-aware and real-server security testing hardens the current health API; [validation](../UI_VALIDATION.md) separates UI completion from future analytical acceptance. No source alignment policy or production architecture approval is inferred.

## Context

The assignment requires React and Python, Elexon WIND actuals and forecast vintages, January buying decisions, a client pitch, and a technical explanation. There is no existing application or established ADR convention in this workspace. Hindsight in forecast selection and mismatched time intervals are greater correctness risks than infrastructure scale.

## Decisions and alternatives

| Decision | Rationale | Alternative and trade-off |
| --- | --- | --- |
| React/TypeScript with Vite and Recharts; FastAPI in Python | Meets the required languages with a direct charting and typed HTTP workflow | Server-rendered Python alone would not meet the React requirement; a larger framework adds scope without a stated need |
| Modular backend with a separate import CLI | One local deployment and explicit boundaries; network-independent browser queries | Microservices or continuous ingestion increase operational work for a fixed historical month |
| SQLite, SQLAlchemy, migrations, and saved raw responses | Small setup burden with relational queries and preserved source provenance | PostgreSQL offers stronger concurrent-write operation but needs another service; CSV-only storage makes revision/conflict queries and snapshot identity harder |
| Immutable dataset membership and content manifests | Same snapshot and policies reproduce results after refresh | Querying all rows ever imported would silently change past results |
| Per-target latest publication at or before cutoff, inclusive boundary | Matches the information available for that target according to source publication time | Latest-now leaks future revisions; a single forecast batch for a whole day can discard valid per-target updates |
| Latest unambiguous actual publication inside the same pinned snapshot | Defines a reproducible retrospective reference | Claiming final settlement truth or historical actual availability is unsupported by the supplied brief |
| Proposed hourly-average comparison only after source validation | Preserves physical meaning and avoids treating cadence as a definition | Duplicating hourly forecasts onto half-hours changes the sampling interpretation; point-time comparison requires different labels and rationale |
| Must metrics: MAE, RMSE, bias, coverage in MW | Exposes magnitude, direction, and missingness without unstable percentage errors | MAPE is unstable near zero; financial metrics require prices and client positions |
| Local, read-only demo without accounts or exchange integration | Uses the public-data scope and avoids an unstated trading workflow | Public deployment needs an explicit hosting, authentication, access, and operational design |

## Defaults and unresolved questions

Interpret January as decision dates, giving 2 January-1 February delivery; default to 09:30 Europe/London as a labelled demo cutoff. Neither is a confirmed client decision. These defaults allow documentation, setup, ingestion, and forecast exploration to proceed.

T01 must resolve filter boundaries, sufficient history extent, revision behavior, and WINDFOR's hourly physical interval meaning. Only the last question blocks the proposed alignment implementation. If hourly-average semantics cannot be established, update the chosen comparison policy and its acceptance criteria before implementing accuracy. Do not declare the entire assignment complete with the accuracy feature unavailable.

## Consequences

The assignment can be demonstrated offline with fixed inputs. Extra snapshot and provenance tables add some storage code, but make the technical explanation and export reconciliation reviewable. The UI must distinguish retrospective evaluation from information visible at a historical decision. Source limitations and missingness stay visible rather than being smoothed away.

The proposal is not an approved production architecture, a source-data guarantee, or evidence of implementation. Change this record to Accepted when the baseline is actually adopted and record the adoption context; do not imply client approval. Substantial later changes should add a superseding ADR rather than delete the original reasoning.
