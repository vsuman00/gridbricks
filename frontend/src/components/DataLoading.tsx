import type { View } from '../types'
import { ScopeNote } from './ScopeNote'

export function DataLoading({ view, cutoff }: { view: View; cutoff: string }) {
  const accuracy = view === 'accuracy'
  const labels = accuracy
    ? ['Mean absolute error · MAE', 'Root mean square error · RMSE', 'Mean bias']
    : ['Forecast coverage', 'Oldest selected publication', 'Unresolved intervals']
  return (
    <section
      className="data-loading"
      role="status"
      aria-busy="true"
      aria-label="Loading stored data"
    >
      <p className="sr-only">Loading stored data. Reading the selected snapshot and filters.</p>
      <div aria-hidden="true">
        <ScopeNote cutoff={cutoff} />
      </div>
      <div className="metrics" aria-hidden="true">
        {labels.map((label) => (
          <div className="metric" key={label}>
            <div className="metric-name">{label}</div>
            <div className="metric-value metric-loading">—</div>
            <div className="metric-foot">
              <span className="loading-line" />
            </div>
          </div>
        ))}
      </div>
      <div className="main-grid" aria-hidden="true">
        <div className="card">
          <div className="card-heading">
            <div>
              <h2>
                {accuracy ? 'Selected forecast vs actual reference' : 'Next-day wind forecast'}
              </h2>
              <p className="card-subtitle">Reading the selected snapshot and filters.</p>
            </div>
          </div>
          <div className="chart-area">
            <div className="skeleton">
              <div />
              <div />
              <div />
              <div />
            </div>
          </div>
          <div className="chart-caption">
            <span>Loading stored observations</span>
          </div>
          <div className="chart-footer">
            <span>No values displayed while loading.</span>
          </div>
        </div>
        <div className="card sidecard loading-context">
          <div className="eyebrow">{accuracy ? 'Retrospective review' : 'Decision context'}</div>
          <h2>Loading stored data</h2>
          <p>Reading the selected snapshot and filters.</p>
          <div className="loading-context-fields">
            <div />
            <div />
            <div />
            <div />
          </div>
        </div>
      </div>
      <div className="card table-card" aria-hidden="true">
        <div className="table-header">
          <h2>Delivery intervals</h2>
          <span>Loading publication provenance</span>
        </div>
        <div className="loading-table">
          <div />
          <div />
          <div />
        </div>
      </div>
    </section>
  )
}
