# T01 source-contract findings

Date: 26 October 2026. Status: source findings support implementation; the application comparison rule is now resolved in [ADR-002](decisions/0002-timestamp-matched-reference.md), using [additional primary research](COMPARISON_POLICY.md). Physical averaging meaning and exhaustive actual-revision history remain explicitly unverified. The original sampled findings below are retained as dated evidence.

## Questions and rulings

| Question | Current result | Evidence and remaining work |
| --- | --- | --- |
| Q01: January scope | Keep decisions 1-31 January and next-day delivery through 1 February | Documented PRD default; no assessor clarification supplied |
| Q02: deadline | Keep configurable 09:30 Europe/London, labelled a demo assumption | No client auction or internal deadline supplied |
| Q03: forecast physical meaning | Physical averaging remains unresolved; `hourly_average_v1` is unsupported. [ADR-002](decisions/0002-timestamp-matched-reference.md) now adopts a visibly limited exact-time half-hour benchmark for accuracy. | [Elexon wind explanation](https://bmrs.elexon.co.uk/wind-generation) describes hourly forecasts; [developer portal](https://developer.data.elexon.co.uk/) describes the derived wind endpoint at a specific point in time. Neither establishes that WINDFOR is a mean over the following hour. |
| Q04: boundaries and actual revisions | Sampled bounds include both endpoints; retain overlap and enforce local bounds | [New evidence](evidence/elexon-t01-source-checks.json): adjacent FUELHH publication windows both contain the midnight boundary. Single-date settlement queries return the full sampled delivery day. Late-revision retrieval completeness remains open; a sample with no revisions does not prove revisions cannot occur |
| Q05: earlier history | Seven-day searches contain eligible forecasts for every next-day target on three sampled decisions | Decisions 1, 15 and 31 January each have 24 eligible target timestamps, including publications exactly at 09:30. This does not prove all dates/cutoffs are covered or that older publications are irrelevant. Retain searched bounds and `history_window_exhausted` handling |
| Q06: conflicts and cadence | No conflicting same-target/publication values or exact duplicates in these samples | Real examples are retained in the evidence. Full-month cadence/conflict auditing belongs to T08; synthetic conflicts remain mandatory tests |
| Q07: actual reference | Keep `latest_in_snapshot_v1` for future retrospective analytics | Three sampled FUELHH delivery days each contain 48 WIND rows and their final 23:30 half-hour. No multiple-publication target was observed in these actual samples. This is neither final settlement truth nor evidence that later actual revisions are absent |

Selection remains `asof_per_target_v1`: greatest publication at or before cutoff per target, with newest-publication conflicts unresolved. The additional research and ADR-002 adopt `timestamp_matched_halfhour_reference_v1` as an application benchmark, not a claim of physical equivalence. This explicit policy and its revised acceptance checks now permit T06 after T04. The January scope is unchanged. The conditional hourly-average fixture examples below are superseded by ADR-002's one exact-time constituent checks; they remain historical proposals, not implemented semantics.

## Live check evidence

The new [source evidence](evidence/elexon-t01-source-checks.json) contains exact URLs, retrieval time, response hashes, counts, publication bounds, and real example records for eight successful requests:

| Decision | Delivery | WINDFOR rows in seven-day publication search | Eligible next-day target timestamps | WIND actual half-hours | Final half-hour |
| --- | --- | --- | --- | --- | --- |
| 2026-01-01 | 2026-01-02 | 4,161 | 24 | 48 | Present |
| 2026-01-15 | 2026-01-16 | 4,161 | 24 | 48 | Present |
| 2026-01-31 | 2026-02-01 | 4,161 | 24 | 48 | Present |

Two further requests inspect adjacent FUELHH publication windows spanning midnight on 16 January; each includes one row at its lower bound and one at its upper bound. Forecast searches also include records at both requested publication bounds. Local half-open target bounds must still be enforced independently of source publication bounds.

For example, the FUELHH record at `2026-02-01T23:30:00Z` is published at `2026-02-02T00:00:00Z` with `fuelType=WIND` and `generation=5302`. A publication search ending before that publication would miss the last half-hour even though the delivery scope ends on 1 February. Use settlement-date filters for delivery coverage, then preserve source publications and available revisions.

Reproduce with a new path so the saved observations remain unchanged:

```bash
python3 scripts/audit_source_contract.py --output /tmp/gridbricks-source-checks-new.json
```

The script is a bounded read-only research helper. It saves summaries, not raw ingestion inputs or immutable application snapshots. It exits nonzero if any request fails, recording that failure distinctly from an empty response. Current samples do not prove API stability, full-month completeness, physical interval meaning, or measured accuracy.

## Future deterministic fixture specification

All values below are synthetic test inputs, not source observations. Their owning tasks must create the fixtures and tests; writing this specification does not implement them.

| Owner | Case | Required assertion |
| --- | --- | --- |
| T04 | A next-day target has 100 MW published at 08:30 and 140 MW at 10:30; cutoff 09:30 | Select 100, retain both vintages, exclude later publication from decision response |
| T04 | A publication is exactly at 09:30; another is one second later | Equality is eligible; the later record is not |
| T04 | A target has only an older-day eligible publication | Use it; do not restrict history to the decision day |
| T03/T04 | Exact duplicate target/publication/value | Deduplicate semantic observation while retaining input lineage |
| T03/T04 | Newest eligible publication has values 100 and 101; older publication has 90 | Retain conflict; leave forecast unresolved, with no row-order choice or fallback |
| T04 | No forecast inside a bounded searched history | Keep the expected grid row and distinguish exhausted history from confirmed source missingness |
| T04 | Decision 31 January | Construct 1 February targets using Europe/London, storing UTC |
| T06, after Q03 | Conditional hourly policy has actuals 80 and 120 at t and t+30m | If validated, one hourly comparison uses mean 100 and retains both constituents |
| T06, after Q03 | One constituent is absent, duplicated, or conflicting | Exact duplicates cannot satisfy a missing half-hour; exclude incomplete/conflicting hours from metrics |
| T06, after Q03 | Actual publication is revised, then latest publication conflicts | Select latest unambiguous reference normally; latest conflict stays unresolved without fallback |
| T06, after Q03 | Forecasts [100, 200], aligned actuals [80, 220] | MAE 20 MW, RMSE 20 MW, bias 0 MW; no matches gives null metrics |
| T03/T07/T10 | Import fails or active snapshot changes between reads | Prior valid active snapshot survives failure; JSON and CSV pin identical immutable membership |

Zero generation must remain a valid value. Expected counts come from the target grid, and missing values remain gaps. Retain actual revisions and raw lineage when ingestion is implemented; this research summary is not a substitute.
