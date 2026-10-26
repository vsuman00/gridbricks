# Retrospective wind comparison policy

Date: 26 October 2026. Status: adopted for implementation by [ADR-002](decisions/0002-timestamp-matched-reference.md), with PRD/architecture/plan/API-contract updates preceding alignment code. This is a benchmark policy choice, not verification of physical averaging equivalence.

## Finding

An hourly WINDFOR timestamp does not establish an hourly average. The [current Elexon schema](https://data.elexon.co.uk/swagger/v1/swagger.json) supplies target time, publication time and generation, with no averaging-duration field. Its FUELHH definition does explicitly identify half-hour average MW. The [developer portal](https://developer.data.elexon.co.uk/) describes the derived wind forecast against a time point. These sources do not establish physical equivalence between WINDFOR and a two-half-hour average.

There is also historical ambiguity. The [2015 IDD](https://assets.elexon.co.uk/wp-content/uploads/sites/11/2015/04/28162953/NETA_IDD_Part_1_v33.0_redlined_P305_P309_CB.pdf) uses peak terminology for WINDFOR and selected half-hours. The [2008 P220 consultation](https://assets.elexon.co.uk/wp-content/uploads/sites/11/2012/02/28170956/p220ac10.pdf) discusses a settlement-period forecast/outturn comparison around a sampled daily peak. [CP1381](https://assets.elexon.co.uk/wp-content/uploads/sites/11/2012/10/28165754/CP1381.pdf) later describes hourly WINDFOR values, including possible negative net generation. None proves that the 2026 stream represents an hourly average, an hourly peak, or an instantaneous measurement.

The [official wind-generation screen](https://bmrs.elexon.co.uk/wind-generation) places forecast values alongside Generation by Fuel Type outturn. Its explanatory text is present in the site's [current application bundle](https://bmrs.elexon.co.uk/static/js/main.8ee28d09.js). This supports a transparent benchmark using the supplied sources. It does not settle the averaging question. A [separate NESO day-ahead series](https://www.neso.energy/data-portal/day-ahead-wind-forecast/day_ahead_wind_forecast) has settlement-period metadata, but is outside the assignment's analytical inputs and is not substituted.

## Recommended policy

Adopt `timestamp_matched_halfhour_reference_v1` as a documented application benchmark. For each hourly WINDFOR target timestamp `t`, select the forecast available at that decision's cutoff and compare it with the FUELHH WIND half-hour whose `startTime` equals `t`. Use exactly one actual constituent, the average for `[t,t+30m)`. The next half-hour is retained in storage but does not enter that target's comparison. Do not average the two half-hours, interpolate an instantaneous actual, or duplicate the forecast onto both half-hours.

Keep the existing `asof_per_target_v1` and `latest_in_snapshot_v1` selection rules. The newest eligible forecast publication and newest actual publication inside the pinned snapshot must each have one unambiguous finite value. Equal-valued duplicates are harmless. A conflicting newest publication stays unresolved without fallback. Publication at the cutoff is eligible; an actual publication after cutoff is permitted only in this retrospective view.

Every accuracy response, data-details panel, CSV and presentation must state: "Timestamp-matched benchmark: WINDFOR compared with the half-hour average starting at the same timestamp; physical averaging equivalence is unverified." Retain a `temporal_reference_mismatch` flag on comparison rows. Keep `target_end` as the hourly display-grid boundary and preserve each constituent's separate half-hour meaning. Never call the actual reference an hourly mean or an instantaneous outturn.

MAE, RMSE and bias remain forecast minus actual-reference MW, using pooled matched targets. They describe this benchmark only. Zero is valid; missing or conflicting exact-time actuals remain gaps even if the adjacent half-hour exists. With no matches, metrics are null. One forecast supplies at most one matched observation. The January scope has 744 expected hourly targets and 744 required benchmark half-hours, while ingestion retains all 1,488 expected actual half-hours and their available revisions.

This choice changes the proposed comparator and its acceptance checks. The parent implementation must revise the PRD, architecture, ADR, integration contract and task criteria before activating it. Source clarification can later supersede this policy without changing historical snapshot membership or silently relabelling existing metrics. `hourly_average_v1` remains unsupported.

## Actual revisions and retrieval limits

The schema permits FUELHH settlement-date queries or publication-time queries, never both filter families together. Delivery-day settlement queries are the baseline for target coverage; publication-window replays can be collected separately and unioned by semantic observation identity, retaining conflicts and raw lineage. Select the latest unambiguous publication actually present in the named snapshot, rather than claiming final settlement truth or a complete revision archive.

Four additional live requests checked 16 January and 1 February, comparing each settlement-date response with a two-day publication window. Each delivery date had 48 target rows in both query families, with identical target/publication/value tuples and no observed multiple-version targets. The last 1 February half-hour was published at 2 February 00:00 UTC. These samples do not prove that later revisions are absent, that all historical revisions are exposed, or that two days is a sufficient general revision horizon.

Exact URLs, hashes, retrieval times, real sample records and source limits are recorded in [comparison research evidence](evidence/t01-comparison-research.json). This research is separate from ingestion snapshots, fixture tests and application accuracy results.

## Required verification after adoption

- An exact-time actual at `t` supplies one constituent; a different value at `t+30m` cannot change the comparison.
- An absent exact-time actual remains missing when the adjacent half-hour exists; duplicate adjacent records cannot fill it.
- Revised actuals use the latest snapshot publication, with a latest-publication conflict unresolved.
- Forecasts `[100, 200]` and exact-time references `[80, 220]` yield MAE 20 MW, RMSE 20 MW and bias 0 MW.
- Charts, API rows, daily summaries and CSV retain the same policy, mismatch label, pinned snapshot and matched-row population.
