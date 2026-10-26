import { useId } from 'react'
import { mw, timestamp, type Analysis, type Interval } from '../api'
import type { View } from '../types'
import { Icon } from './Icon'
import { ScopeNote } from './ScopeNote'

function DataPlot({ rows, accuracy }: { rows: Interval[]; accuracy: boolean }) {
  const id = useId()
  const values = rows
    .flatMap((row) => [row.forecast_mw, ...(accuracy ? [row.actual_mw] : [])])
    .filter((value): value is number => value != null)
  const lower = Math.min(0, ...values)
  const upper = Math.max(0, ...values)
  const padding = Math.max(1, upper - lower) * 0.08
  const minimum = lower < 0 ? lower - padding : 0
  const maximum = upper > 0 ? upper + padding : lower < 0 ? 0 : 1
  const first = Date.parse(rows[0].target_start)
  const last = Date.parse(rows[rows.length - 1].target_start)
  const x = (row: Interval) =>
    55 + ((Date.parse(row.target_start) - first) / Math.max(1, last - first)) * 710
  const y = (value: number) => 225 - ((value - minimum) / (maximum - minimum)) * 195
  function path(field: 'forecast_mw' | 'actual_mw') {
    let pen = false
    return rows
      .map((row, index) => {
        const value = row[field]
        if (value == null) {
          pen = false
          return ''
        }
        const continuous = index === 0 || rows[index - 1].target_end === row.target_start
        const point = `${pen && continuous ? 'L' : 'M'}${x(row)},${y(value)}`
        pen = true
        return point
      })
      .join(' ')
  }
  const tickRows = [...new Set([0, Math.floor((rows.length - 1) / 2), rows.length - 1])].map(
    (index) => rows[index],
  )
  return (
    <svg
      className="plot data-plot"
      viewBox="0 0 790 265"
      role="img"
      aria-labelledby={`${id}-title ${id}-desc`}
    >
      <title id={`${id}-title`}>
        {accuracy
          ? 'Selected forecast and later actual wind reference'
          : 'Wind forecast available at cutoff'}
      </title>
      <desc id={`${id}-desc`}>
        Power in MW. Gaps mark unavailable or unresolved values. Exact values and source provenance
        are in the delivery interval table.
      </desc>
      <g className="chart-grid">
        {[0, 1, 2, 3, 4].map((tick) => (
          <line key={tick} x1="55" x2="765" y1={225 - tick * 48.75} y2={225 - tick * 48.75} />
        ))}
      </g>
      <g className="chart-labels">
        <text x="4" y="15">
          MW
        </text>
        {[0, 1, 2, 3, 4].map((tick) => (
          <text key={tick} x="3" y={229 - tick * 48.75}>
            {mw(minimum + ((maximum - minimum) * tick) / 4)}
          </text>
        ))}
        {tickRows.map((row, index) => (
          <text
            key={row.target_start}
            x={x(row)}
            y="250"
            textAnchor={index === 0 ? 'start' : index === tickRows.length - 1 ? 'end' : 'middle'}
          >
            {new Intl.DateTimeFormat('en-GB', {
              ...(accuracy
                ? { day: '2-digit', month: 'short' }
                : { hour: '2-digit', minute: '2-digit' }),
              timeZone: 'Europe/London',
            }).format(new Date(row.target_start))}
          </text>
        ))}
      </g>
      {minimum < 0 && (
        <g>
          <line className="zero-line" x1="55" x2="765" y1={y(0)} y2={y(0)} />
          {maximum > 0 && (
            <text className="chart-labels" x="40" y={y(0) + 4}>
              0
            </text>
          )}
        </g>
      )}
      <path
        className="forecast-curve"
        pathLength="1"
        d={path('forecast_mw')}
        fill="none"
        stroke="var(--teal)"
        strokeWidth="2.6"
      />
      {accuracy && <path className="actual-line" d={path('actual_mw')} />}
      {rows.map((row) => (
        <g key={row.target_start}>
          {row.forecast_mw != null && (
            <circle cx={x(row)} cy={y(row.forecast_mw)} r="2" fill="var(--teal)">
              <title>
                {timestamp(row.target_start)}: forecast {mw(row.forecast_mw)} MW; published{' '}
                {timestamp(row.forecast_publish_time)}
              </title>
            </circle>
          )}
          {accuracy && row.actual_mw != null && (
            <circle cx={x(row)} cy={y(row.actual_mw)} r="2" fill="#6d7d8c">
              <title>
                {timestamp(row.target_start)}: actual {mw(row.actual_mw)} MW
              </title>
            </circle>
          )}
        </g>
      ))}
    </svg>
  )
}
function Errors({ rows }: { rows: Interval[] }) {
  const maximum = Math.max(1, ...rows.map((row) => Math.abs(row.error_mw ?? 0)))
  return (
    <section className="card error-card" aria-labelledby="error-title">
      <div className="card-heading">
        <div>
          <h2 id="error-title">Forecast error</h2>
          <p className="card-subtitle">Forecast minus actual · positive means overforecast wind</p>
        </div>
        <span className="badge">MW</span>
      </div>
      <svg
        className="error-plot"
        viewBox="0 0 790 130"
        role="img"
        aria-label="Signed interval errors in MW; exact values available in the interval table"
      >
        <line className="zero-line" x1="40" x2="770" y1="65" y2="65" />
        <text className="chart-labels" x="4" y="69">
          0
        </text>
        <text className="chart-labels" x="4" y="17">
          +{mw(maximum)}
        </text>
        <text className="chart-labels" x="4" y="121">
          −{mw(maximum)}
        </text>
        {rows.map((row, index) =>
          row.error_mw == null ? null : (
            <rect
              key={row.target_start}
              x={40 + (index * 730) / rows.length}
              width={Math.max(0.6, (730 / rows.length) * 0.7)}
              y={row.error_mw >= 0 ? 65 - (row.error_mw / maximum) * 50 : 65}
              height={Math.max(0.7, (Math.abs(row.error_mw) / maximum) * 50)}
              className={row.error_mw >= 0 ? 'bar-positive' : 'bar-negative'}
            >
              <title>
                {timestamp(row.target_start)}: {mw(row.error_mw, true)} MW
              </title>
            </rect>
          ),
        )}
      </svg>
    </section>
  )
}
export function DataOverview({
  data,
  view,
  onOpenDetails,
}: {
  data: Analysis
  view: View
  onOpenDetails: () => void
}) {
  const accuracy = view === 'accuracy'
  const { coverage, meta } = data
  const reasons = Object.entries(coverage.reason_counts).filter(
    ([reason, count]) => count > 0 && !['selected', 'matched'].includes(reason),
  )
  const incomplete = accuracy
    ? (coverage.matched_count ?? 0) < coverage.expected_count
    : coverage.forecast_selected_count < coverage.expected_count
  const ages = data.rows.flatMap((row) =>
    row.forecast_age_hours == null ? [] : [row.forecast_age_hours],
  )
  const metrics = accuracy
    ? [
        ['Mean absolute error · MAE', mw(data.metrics?.mae_mw), 'MW', 'Pooled matched intervals'],
        [
          'Root mean square error · RMSE',
          mw(data.metrics?.rmse_mw),
          'MW',
          'More sensitive to large misses',
        ],
        [
          'Mean bias',
          mw(data.metrics?.bias_mw, true),
          'MW',
          'Positive means wind was overforecast',
        ],
      ]
    : [
        [
          'Forecast coverage',
          String(coverage.forecast_selected_count),
          `/ ${coverage.expected_count} targets`,
          'Eligible and unambiguous forecasts',
        ],
        [
          'Oldest selected publication',
          ages.length ? mw(Math.max(...ages)) : '—',
          'hours',
          'Age measured at the selected cutoff',
        ],
        [
          'Unresolved intervals',
          String(coverage.expected_count - coverage.forecast_selected_count),
          'targets',
          'Missing or conflicting forecasts',
        ],
      ]
  return (
    <>
      <ScopeNote cutoff={meta.cutoff_local} />
      {meta.source_mode === 'fixture' && (
        <div className="quality-banner" role="status">
          Synthetic fixture dataset. These are demonstration observations, not measured Elexon
          results.
        </div>
      )}
      {incomplete && reasons.length > 0 && (
        <div className="quality-banner" role="status">
          <Icon name="warning" />
          <span>
            Incomplete coverage.{' '}
            {reasons
              .map(([reason, count]) => `${reason.replaceAll('_', ' ')}: ${count}`)
              .join(' · ')}
            . Missing and conflicting values remain gaps.
          </span>
        </div>
      )}
      {accuracy && coverage.matched_count === 1 && (
        <div className="quality-banner" role="note">
          Limited sample: n = 1 matched interval. These metrics describe one observation and do not
          establish typical forecast accuracy.
        </div>
      )}
      {accuracy && meta.comparison_note && (
        <div className="quality-banner comparison-note" role="note">
          <Icon name="info" />
          <span>{meta.comparison_note}</span>
        </div>
      )}
      <div className="metrics" aria-label={accuracy ? 'Accuracy metrics' : 'Forecast summary'}>
        {metrics.map(([name, value, unit, foot]) => (
          <section className="metric" key={name}>
            <div className="metric-name">{name}</div>
            <div className="metric-value">
              {value} <small>{unit}</small>
            </div>
            <div className="metric-foot">{foot}</div>
          </section>
        ))}
      </div>
      {accuracy && (
        <div className="coverage-strip">
          <span>
            Matched intervals{' '}
            <b>
              {coverage.matched_count ?? 0} / {coverage.expected_count}
            </b>
          </span>
          <span>
            Coverage{' '}
            <b>
              {coverage.matched_fraction == null
                ? 'Unavailable'
                : `${mw(coverage.matched_fraction * 100)}%`}
            </b>
          </span>
          <span>
            Complete actual intervals <b>{coverage.complete_actual_count ?? 0}</b>
          </span>
          <span>Retrospective comparison</span>
        </div>
      )}
      <div className="main-grid">
        <div>
          <section className="card" aria-labelledby="chart-title">
            <div className="card-heading">
              <div>
                <h2 id="chart-title">
                  {accuracy ? 'Selected forecast vs actual reference' : 'Next-day wind forecast'}
                </h2>
                <p className="card-subtitle">
                  Delivery · {meta.delivery_from}
                  {meta.delivery_to !== meta.delivery_from && ` to ${meta.delivery_to}`}
                </p>
              </div>
              <div className="legend">
                <span>
                  <i className="swatch" />
                  Forecast
                </span>
                {accuracy && (
                  <span>
                    <i className="swatch actual" />
                    Actual reference
                  </span>
                )}
              </div>
            </div>
            <div className="chart-area">
              {data.rows.length > 0 &&
              (coverage.forecast_selected_count > 0 ||
                (accuracy && (coverage.complete_actual_count ?? 0) > 0)) ? (
                <DataPlot rows={data.rows} accuracy={accuracy} />
              ) : (
                <div className="state-message" role="status">
                  <strong>{accuracy ? 'No matched observations' : 'No eligible forecast'}</strong>
                  <p>
                    Values are unavailable for this selection. Inspect the interval reasons below or
                    choose another date or cutoff.
                  </p>
                </div>
              )}
            </div>
            <div className="chart-caption">
              <span>Snapshot {meta.snapshot_id.slice(0, 12)} · gaps preserved</span>
              <span>Delivery time · UK</span>
            </div>
            <div className="chart-footer">
              <span>
                <Icon name="info" />
                {accuracy
                  ? 'Later actuals are used only for retrospective review.'
                  : 'Newest eligible publication selected separately per target.'}
              </span>
              <a href="#intervals" onClick={() => document.getElementById('intervals')?.focus()}>
                View table ↓
              </a>
            </div>
          </section>
          {accuracy && data.rows.some((row) => row.error_mw != null) && <Errors rows={data.rows} />}
        </div>
        <aside className="card sidecard" aria-labelledby="context-title">
          <div className="eyebrow">{accuracy ? 'Retrospective review' : 'Decision context'}</div>
          <h2 id="context-title">
            {accuracy ? 'Read the error in context' : 'Available at your cutoff'}
          </h2>
          <p>
            {accuracy
              ? 'Each forecast is selected at its historical buying cutoff, then compared with later wind outturn.'
              : 'Revisions published after the cutoff are excluded. Conflicts remain unresolved.'}
          </p>
          <dl className="metadata">
            <div>
              <dt>Decision period</dt>
              <dd>
                {meta.decision_from}
                {meta.decision_to !== meta.decision_from && ` to ${meta.decision_to}`}
              </dd>
            </div>
            <div>
              <dt>Buying cutoff</dt>
              <dd>{meta.cutoff_local} UK</dd>
            </div>
            <div>
              <dt>Forecast source</dt>
              <dd>WINDFOR</dd>
            </div>
            {accuracy && (
              <div>
                <dt>Actual source</dt>
                <dd>FUELHH · WIND</dd>
              </div>
            )}
            <div>
              <dt>Dataset</dt>
              <dd>
                {meta.source_mode === 'fixture' ? 'Synthetic fixture' : 'Live-source snapshot'}
              </dd>
            </div>
            <div>
              <dt>Retrieved at · UK</dt>
              <dd>{timestamp(meta.retrieved_at)}</dd>
            </div>
          </dl>
          <div className="aside-note">
            <strong>Reproducible analysis</strong>Charts, tables and CSV use this same immutable
            snapshot. Null values stay missing; zero MW is a real observation.
            {accuracy && (
              <p>
                MAE is the mean absolute error. RMSE is the square root of the mean squared error.
                Bias is the mean signed error. Each uses pooled matched intervals.
              </p>
            )}
          </div>
          <button type="button" className="text-button details-link" onClick={onOpenDetails}>
            Inspect data details
            <Icon name="arrow" />
          </button>
        </aside>
      </div>
    </>
  )
}
