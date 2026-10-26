import { useState } from 'react'
import { mw, timestamp, type Analysis, type Interval, type Lineage } from '../api'
import type { View } from '../types'

function Sources({ sources }: { sources: Lineage[] }) {
  return sources.length ? (
    <ul className="lineage-list">
      {sources.map((source, index) => (
        <li key={`${source.raw_response_id}-${source.row_index}-${index}`}>
          Response <code>{source.raw_response_id}</code>, row {source.row_index}; retrieved{' '}
          {timestamp(source.retrieved_at)} UK; SHA-256 <code>{source.content_hash}</code>
          <br />
          Request <code>{source.request_url}</code>
        </li>
      ))}
    </ul>
  ) : (
    <span>No source lineage for this value.</span>
  )
}
function Provenance({ row, accuracy }: { row: Interval; accuracy: boolean }) {
  return (
    <details className="provenance">
      <summary>Inspect source records</summary>
      <div>
        <p>
          Forecast observation: <code>{row.forecast_observation_id ?? 'Unavailable'}</code>
        </p>
        <p>
          Cutoff: {timestamp(row.cutoff_utc)} UK · decision {row.decision_date}
        </p>
        <Sources sources={row.forecast_sources} />
        {accuracy && (
          <>
            <p>Actual constituent records ({row.actual_constituents?.length ?? 0})</p>
            {row.actual_constituents?.map((actual) => (
              <div key={actual.observation_id}>
                <p>
                  <code>{actual.observation_id}</code> · half-hour reference [
                  {timestamp(actual.start_time)}, {timestamp(actual.end_time)}) UK · publication{' '}
                  {timestamp(actual.publish_time)} UK · {mw(actual.generation_mw)} MW
                </p>
                <Sources sources={actual.raw_sources} />
              </div>
            ))}
          </>
        )}
        {row.flags.length > 0 && <p>Flags: {row.flags.join(', ')}</p>}
      </div>
    </details>
  )
}
export function DataTables({ data, view }: { data: Analysis; view: View }) {
  const [expanded, setExpanded] = useState(false)
  const [page, setPage] = useState(0)
  const accuracy = view === 'accuracy'
  const pageSize = expanded ? 24 : 3
  const pageCount = Math.max(1, Math.ceil(data.rows.length / pageSize))
  const current = Math.min(page, pageCount - 1)
  const rows = data.rows.slice(current * pageSize, current * pageSize + pageSize)
  return (
    <>
      <section
        className="card table-card"
        id="intervals"
        tabIndex={-1}
        aria-labelledby="table-title"
      >
        <div className="table-header">
          <h2 id="table-title">Delivery intervals</h2>
          <span>
            Snapshot {data.meta.snapshot_id.slice(0, 12)} · publication provenance retained
          </span>
        </div>
        <div
          className="table-wrap"
          role="region"
          aria-label="Delivery interval observations"
          tabIndex={0}
        >
          <table>
            <caption className="sr-only">
              All expected targets from the current snapshot. Gaps remain unavailable. Times are
              Europe/London. Values display to two decimals; CSV retains full precision.
            </caption>
            <thead>
              <tr>
                <th scope="col">Delivery date / time · UK</th>
                <th scope="col" className="num">
                  Forecast · MW
                </th>
                {accuracy && (
                  <>
                    <th scope="col" className="num">
                      Actual reference · MW
                    </th>
                    <th scope="col" className="num">
                      Error · MW
                    </th>
                  </>
                )}
                <th scope="col">Published at · UK</th>
                <th scope="col" className="num">
                  Age at cutoff · h
                </th>
                <th scope="col" className="num">
                  Lead to target · h
                </th>
                <th scope="col">Status / provenance</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.decision_date}-${row.target_start}`}>
                  <th scope="row">{timestamp(row.target_start)}</th>
                  <td className="num">{mw(row.forecast_mw)}</td>
                  {accuracy && (
                    <>
                      <td className="num">{mw(row.actual_mw)}</td>
                      <td className="num">{mw(row.error_mw, true)}</td>
                    </>
                  )}
                  <td>{timestamp(row.forecast_publish_time)}</td>
                  <td className="num">{mw(row.forecast_age_hours)}</td>
                  <td className="num">{mw(row.forecast_lead_hours)}</td>
                  <td>
                    <span
                      className={`row-state${row.forecast_mw == null || (accuracy && row.error_mw == null) ? ' missing' : ''}`}
                    >
                      {row.state.replaceAll('_', ' ')}
                    </span>
                    <Provenance row={row} accuracy={accuracy} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-bottom">
          <span>
            {data.rows.length
              ? `${current * pageSize + 1}–${Math.min((current + 1) * pageSize, data.rows.length)} of ${data.rows.length} expected intervals`
              : 'No interval rows returned'}
          </span>
          <span>— means unavailable · zero is retained</span>
        </div>
        <div className="table-actions">
          <button
            className="text-button"
            type="button"
            aria-expanded={expanded}
            onClick={() => {
              setExpanded(!expanded)
              setPage(0)
            }}
          >
            {expanded ? 'Show fewer intervals' : `Show all ${data.rows.length} intervals`}
          </button>
          {expanded && pageCount > 1 && (
            <div className="pagination" aria-label="Interval table pagination">
              <button
                type="button"
                className="button"
                disabled={current === 0}
                onClick={() => setPage(current - 1)}
              >
                Previous intervals
              </button>
              <span aria-live="polite">
                Page {current + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="button"
                disabled={current === pageCount - 1}
                onClick={() => setPage(current + 1)}
              >
                Next intervals
              </button>
            </div>
          )}
        </div>
      </section>
      {accuracy && (
        <section className="card daily-card" aria-labelledby="daily-title">
          <div className="table-header">
            <h2 id="daily-title">Daily accuracy</h2>
            <span>Server-calculated daily metrics · pooled metrics above</span>
          </div>
          <div
            className="table-wrap"
            role="region"
            aria-label="Daily accuracy observations"
            tabIndex={0}
          >
            <table>
              <caption className="sr-only">
                Daily retrospective accuracy for the same immutable snapshot and cutoff. No matches
                means unavailable metrics.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Decision date</th>
                  <th scope="col">Delivery date</th>
                  <th scope="col" className="num">
                    MAE · MW
                  </th>
                  <th scope="col" className="num">
                    RMSE · MW
                  </th>
                  <th scope="col" className="num">
                    Bias · MW
                  </th>
                  <th scope="col">Matched / expected</th>
                  <th scope="col">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {data.daily?.map((day) => (
                  <tr key={day.decision_date}>
                    <th scope="row">{day.decision_date}</th>
                    <td>{day.delivery_date}</td>
                    <td className="num">{mw(day.mae_mw)}</td>
                    <td className="num">{mw(day.rmse_mw)}</td>
                    <td className="num">{mw(day.bias_mw, true)}</td>
                    <td>
                      {day.matched_count} / {day.expected_count}
                    </td>
                    <td>{mw(day.matched_fraction * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-bottom">
            <span>{data.daily?.length ?? 0} decision days · retrospective review</span>
            <span>Forecast minus actual</span>
          </div>
        </section>
      )}
    </>
  )
}
