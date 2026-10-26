// Validate the fields rendered by the UI before accepting an API response.
// Selection, alignment and metric calculations remain in the Python service.
type ObjectValue = Record<string, unknown>

function object(value: unknown): value is ObjectValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
function text(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}
function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}
function nullableNumber(value: unknown) {
  return value === null || finite(value)
}
function count(value: unknown) {
  return finite(value) && Number.isInteger(value) && value >= 0
}
function fraction(value: unknown) {
  return finite(value) && value >= 0 && value <= 1
}
function strings(value: ObjectValue, names: string[]) {
  return names.every((name) => text(value[name]))
}
function stringList(value: unknown) {
  return Array.isArray(value) && value.every(text)
}
function counts(value: unknown) {
  return object(value) && Object.values(value).every(count)
}
function policies(value: unknown) {
  return object(value) && Object.values(value).every(text)
}
export function validSnapshotId(value: unknown) {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value)
}
function date(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value
}
function decisionDate(value: unknown) {
  return date(value) && value >= '2026-01-01' && value <= '2026-01-31'
}
function deliveryDate(value: unknown) {
  return date(value) && value >= '2026-01-02' && value <= '2026-02-01'
}
function timestamp(value: unknown) {
  return (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|\+00:00)$/.test(value) &&
    date(value.slice(0, 10)) &&
    Number.isFinite(Date.parse(value))
  )
}
function nullableTimestamp(value: unknown) {
  return value === null || timestamp(value)
}
function bounds(value: ObjectValue) {
  return (
    decisionDate(value.decision_from) &&
    decisionDate(value.decision_to) &&
    (value.decision_from as string) <= (value.decision_to as string) &&
    deliveryDate(value.delivery_from) &&
    deliveryDate(value.delivery_to) &&
    (value.delivery_from as string) <= (value.delivery_to as string)
  )
}
function sourceMode(value: unknown) {
  return value === 'fixture' || value === 'live'
}
function snapshot(value: unknown) {
  return (
    object(value) &&
    validSnapshotId(value.snapshot_id) &&
    strings(value, ['input_hash', 'status']) &&
    timestamp(value.created_at) &&
    timestamp(value.retrieved_at) &&
    sourceMode(value.source_mode) &&
    bounds(value) &&
    policies(value.policies) &&
    counts(value.counts)
  )
}
function lastImport(value: unknown) {
  return (
    value === null ||
    (object(value) &&
      text(value.status) &&
      (value.id === undefined || text(value.id)) &&
      (value.completed_at === undefined || nullableTimestamp(value.completed_at)) &&
      (value.error_code === undefined || value.error_code === null || text(value.error_code)) &&
      (value.counts === undefined || counts(value.counts)))
  )
}
function dataStatus(value: ObjectValue) {
  return (
    (value.snapshot === null || snapshot(value.snapshot)) &&
    lastImport(value.last_import) &&
    object(value.alignment) &&
    typeof value.alignment.verified === 'boolean' &&
    (value.alignment.policy === null || text(value.alignment.policy)) &&
    text(value.alignment.message) &&
    Array.isArray(value.sources) &&
    value.sources.every((source) => object(source) && strings(source, ['dataset', 'url']))
  )
}
function lineage(value: unknown) {
  return (
    Array.isArray(value) &&
    value.every(
      (entry) =>
        object(entry) &&
        strings(entry, ['raw_response_id', 'content_hash', 'request_url']) &&
        count(entry.row_index) &&
        timestamp(entry.retrieved_at),
    )
  )
}
function constituent(value: unknown) {
  return (
    object(value) &&
    text(value.observation_id) &&
    timestamp(value.start_time) &&
    (value.end_time === undefined || timestamp(value.end_time)) &&
    timestamp(value.publish_time) &&
    finite(value.generation_mw) &&
    lineage(value.raw_sources)
  )
}
function interval(value: unknown, accuracy: boolean) {
  if (
    !object(value) ||
    !decisionDate(value.decision_date) ||
    !timestamp(value.cutoff_utc) ||
    !timestamp(value.target_start) ||
    !timestamp(value.target_end) ||
    !nullableNumber(value.forecast_mw) ||
    !nullableTimestamp(value.forecast_publish_time) ||
    !(value.forecast_observation_id === null || text(value.forecast_observation_id)) ||
    !nullableNumber(value.forecast_age_hours) ||
    !nullableNumber(value.forecast_lead_hours) ||
    !lineage(value.forecast_sources) ||
    !text(value.state) ||
    !stringList(value.flags)
  )
    return false
  return accuracy
    ? nullableNumber(value.actual_mw) &&
        nullableNumber(value.error_mw) &&
        Array.isArray(value.actual_constituents) &&
        value.actual_constituents.every(constituent)
    : !('actual_mw' in value) && !('error_mw' in value) && !('actual_constituents' in value)
}
function metrics(value: unknown) {
  return (
    object(value) && ['mae_mw', 'rmse_mw', 'bias_mw'].every((name) => nullableNumber(value[name]))
  )
}
function coverage(value: unknown, accuracy: boolean) {
  return (
    object(value) &&
    count(value.expected_count) &&
    count(value.forecast_selected_count) &&
    counts(value.reason_counts) &&
    (!accuracy ||
      (count(value.complete_actual_count) &&
        count(value.matched_count) &&
        fraction(value.matched_fraction)))
  )
}
function daily(value: unknown) {
  return (
    object(value) &&
    decisionDate(value.decision_date) &&
    deliveryDate(value.delivery_date) &&
    ['expected_count', 'forecast_selected_count', 'complete_actual_count', 'matched_count'].every(
      (name) => count(value[name]),
    ) &&
    fraction(value.matched_fraction) &&
    metrics(value)
  )
}
function analysis(value: ObjectValue, accuracy: boolean) {
  const meta = value.meta
  return (
    object(meta) &&
    validSnapshotId(meta.snapshot_id) &&
    bounds(meta) &&
    strings(meta, [
      'input_hash',
      'selection_policy',
      'actual_policy',
      'metric_policy',
      'evaluation_mode',
    ]) &&
    timestamp(meta.retrieved_at) &&
    sourceMode(meta.source_mode) &&
    typeof meta.cutoff_local === 'string' &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(meta.cutoff_local) &&
    meta.timezone === 'Europe/London' &&
    meta.unit === 'MW' &&
    count(meta.comparison_resolution_minutes) &&
    (meta.comparison_resolution_minutes as number) > 0 &&
    (meta.alignment_policy === null || text(meta.alignment_policy)) &&
    (meta.comparison_note === undefined || text(meta.comparison_note)) &&
    coverage(value.coverage, accuracy) &&
    Array.isArray(value.rows) &&
    value.rows.length <= 744 &&
    value.rows.every((row) => interval(row, accuracy)) &&
    (!accuracy ||
      (metrics(value.metrics) && Array.isArray(value.daily) && value.daily.every(daily)))
  )
}
export function validApiResponse(path: string, value: unknown) {
  if (!object(value)) return false
  if (path.startsWith('data-status')) return dataStatus(value)
  if (path.startsWith('forecast?')) return analysis(value, false)
  if (path.startsWith('accuracy?')) return analysis(value, true)
  return true
}
