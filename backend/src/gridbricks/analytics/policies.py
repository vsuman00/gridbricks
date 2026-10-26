ALIGNMENT_POLICY = "timestamp_matched_halfhour_reference_v1"
COMPARISON_NOTE = (
    "Timestamp-matched benchmark: WINDFOR compared with the half-hour average starting at the "
    "same timestamp; physical averaging equivalence is unverified."
)
POLICIES = {
    "selection": "asof_per_target_v1",
    "alignment": ALIGNMENT_POLICY,
    "actual": "latest_in_snapshot_v1",
    "metric": "pooled_errors_v1",
}
