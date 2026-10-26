# ADR-002: Timestamp-matched half-hour reference benchmark

Status: Accepted for this assignment implementation, 26 October 2026. This is an application policy choice under the user's instruction to complete the project, not client approval or a new source definition. It supersedes ADR-001's conditional hourly-average comparator only.

## Evidence and decision

[Primary-source research](../COMPARISON_POLICY.md) found no definition establishing that the current WINDFOR stream is an average over the following hour. Current Elexon documentation relates the forecast to a target timestamp; historical documents use different peak/settlement terminology. FUELHH explicitly supplies half-hour average MW. The official Elexon wind screen compares these supplied sources, but does not prove temporal equivalence.

Adopt `timestamp_matched_halfhour_reference_v1`: each selected WINDFOR target at `t` is compared once with the FUELHH WIND average for `[t,t+30m)`, selected by exact start-time equality and latest unambiguous publication in the pinned snapshot. The adjacent half-hour remains stored but is not another sample and does not alter this target's reference. This is a transparent benchmark, not an hourly-average or instantaneous-outturn claim. `hourly_average_v1` remains unsupported.

Every accuracy response/export and the visible accuracy workflow must state the comparison policy and temporal limitation. Comparison rows retain `temporal_reference_mismatch`; actual constituents retain their own start/publication/value/lineage. The forecast target's `target_end` is an hourly display-grid boundary only. MAE/RMSE/bias describe forecast minus this actual reference in MW, pooled across matched targets; null metrics remain null with no matches.

January has 744 expected forecast targets and 744 required exact-time reference half-hours for this benchmark. Ingestion still retains all 1,488 expected half-hours and available revisions. Conflicting latest publications stay unresolved. No interpolation, adjacent substitution, forecast duplication, MWh summary, final-settlement claim or new data feed is introduced.

## Consequences and acceptance

This resolves the application comparison rule while leaving the physical WINDFOR averaging definition explicitly unverified. It enables retrospective reference-benchmark functionality with a visible limitation. It cannot support a claim of physically equivalent hourly energy accuracy. A future source clarification requires a new policy/version and new snapshot manifest rather than silently changing pinned results.

Tests must prove exact-time matching; adjacent rows cannot fill a missing constituent or change a present one. Latest actual revisions and conflicts, cutoff equality, pooled equations, source identity, immutable snapshots and CSV parity remain mandatory. The PRD, architecture, implementation plan, source-contract note and API contract adopt this rule before alignment implementation.
