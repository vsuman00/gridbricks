import type { ReactNode } from 'react'
import type { View } from '../types'
import { Icon } from './Icon'

interface Props {
  view: View
  sourceMode?: 'fixture' | 'live'
  onViewChange: (view: View) => void
  onOpenDetails: () => void
  exportHref?: string
  children: ReactNode
}

export function Layout({
  view,
  sourceMode,
  onViewChange,
  onOpenDetails,
  children,
  exportHref,
}: Props) {
  const accuracy = view === 'accuracy'
  return (
    <>
      <a
        className="skip-link"
        href="#main"
        onClick={() => document.getElementById('main')?.focus()}
      >
        Skip to content
      </a>
      <div className="shell">
        <aside className="sidebar" aria-label="Workspace navigation">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
            </span>
            GridBricks
          </div>
          <div>
            <div className="workspace-label">Wind intelligence</div>
            <nav aria-label="Main views">
              <button
                type="button"
                className="nav-button"
                aria-current={!accuracy ? 'page' : undefined}
                onClick={() => onViewChange('decision')}
              >
                <Icon name="chart" />
                Decision view
              </button>
              <button
                type="button"
                className="nav-button"
                aria-current={accuracy ? 'page' : undefined}
                onClick={() => onViewChange('accuracy')}
              >
                <Icon name="accuracy" />
                Accuracy
              </button>
            </nav>
          </div>
          <div className="sidebar-footer">
            <strong>January 2026</strong>
            <p>Historical decision workspace</p>
            <button className="text-button" type="button" onClick={onOpenDetails}>
              <Icon name="data" />
              Data details
            </button>
          </div>
        </aside>
        <div className="content">
          <main id="main" tabIndex={-1}>
            <div className="page-heading">
              <div>
                <h1>{accuracy ? 'Forecast accuracy' : 'Wind outlook'}</h1>
                <p className="subtitle">
                  {accuracy
                    ? 'Compare forecasts selected at each buying cutoff with later wind generation.'
                    : 'The forecast available before your day-ahead buying deadline.'}
                </p>
              </div>
              <div className="export-control">
                {exportHref ? (
                  <a className="button" href={exportHref}>
                    <Icon name="download" />
                    <span>Export CSV</span>
                  </a>
                ) : (
                  <button
                    className="button"
                    type="button"
                    disabled
                    aria-describedby="export-reason"
                  >
                    <Icon name="download" />
                    <span>Export CSV</span>
                  </button>
                )}
                <p id="export-reason">
                  {exportHref
                    ? 'Current filters · pinned snapshot'
                    : 'Available after a stored response loads'}
                </p>
              </div>
            </div>
            {children}
            <footer className="page-footer">
              <span>
                {sourceMode === 'live' ? (
                  <>
                    Contains BMRS data © Elexon Limited copyright and database right 2026.{' '}
                    <a href="https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/">
                      Data licence
                    </a>
                  </>
                ) : sourceMode === 'fixture' ? (
                  'Synthetic fixture data for demonstration'
                ) : (
                  'Data source shown after loading'
                )}
              </span>
              <button className="text-button" type="button" onClick={onOpenDetails}>
                Sources &amp; methodology
              </button>
            </footer>
          </main>
        </div>
      </div>
    </>
  )
}
