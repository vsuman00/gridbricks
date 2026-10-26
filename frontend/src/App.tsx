import { useEffect, useRef, useState } from 'react'
import { ApiError, analysisQuery, exportUrl, type Analysis, type DataStatus } from './api'
import { DataDetails } from './components/DataDetails'
import { DataOverview } from './components/DataOverview'
import { DataLoading } from './components/DataLoading'
import { DataTables } from './components/DataTables'
import { Filters } from './components/Filters'
import { Layout } from './components/Layout'
import { useData } from './useData'
import { useWorkspace } from './useWorkspace'

export default function App() {
  const workspace = useWorkspace()
  const [detailsOpen, setDetailsOpen] = useState(false)
  const opener = useRef<HTMLElement | null>(null)
  const { view, filters, snapshotId } = workspace
  const status = useData<DataStatus>(
    workspace.warning
      ? null
      : `data-status${snapshotId ? `?${new URLSearchParams({ snapshot_id: snapshotId })}` : ''}`,
  )
  const snapshot = status.data?.snapshot
  const { pinSnapshot } = workspace
  useEffect(() => {
    if (!snapshotId && snapshot) pinSnapshot(snapshot)
  }, [snapshotId, snapshot, pinSnapshot])
  const path =
    !workspace.warning && snapshotId
      ? `${view === 'decision' ? 'forecast' : 'accuracy'}?${analysisQuery(view, filters, snapshotId)}`
      : null
  const analysis = useData<Analysis>(path)
  const filterKey = `${view}-${filters.decisionFrom}-${filters.decisionTo}-${filters.cutoff}-${snapshotId}`
  const mismatch = analysis.data && snapshotId && analysis.data.meta.snapshot_id !== snapshotId
  const error =
    status.error ??
    analysis.error ??
    (mismatch
      ? new ApiError(
          'snapshot_mismatch',
          'The API response did not match the pinned snapshot. Retry the request.',
        )
      : undefined)
  const loading = status.loading || analysis.loading || (!!snapshot && !snapshotId)
  const data = !error && !loading ? analysis.data : undefined
  const exportHref =
    data && snapshotId && data.meta.snapshot_id === snapshotId
      ? exportUrl(view, filters, snapshotId)
      : undefined
  const staleSnapshot = error?.status === 404 && !!snapshotId
  useEffect(() => {
    document.title = `${view === 'accuracy' ? 'Forecast accuracy' : 'Wind outlook'} | GridBricks`
  }, [view])
  function openDetails() {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setDetailsOpen(true)
  }
  function closeDetails() {
    setDetailsOpen(false)
    opener.current?.focus()
  }
  function retry() {
    status.retry()
    analysis.retry()
  }
  return (
    <>
      <Layout
        view={view}
        sourceMode={snapshot?.source_mode}
        onViewChange={workspace.selectView}
        onOpenDetails={openDetails}
        exportHref={exportHref}
      >
        {workspace.warning && (
          <div className="quality-banner url-warning" role="alert">
            <span>{workspace.warning}</span>
            <button className="text-button" type="button" onClick={workspace.resetLink}>
              Reset link
            </button>
          </div>
        )}
        <Filters key={filterKey} view={view} filters={filters} onApply={workspace.applyFilters} />
        {snapshot && status.data?.last_import?.status === 'failed' && (
          <div className="quality-banner" role="status">
            The latest import failed
            {status.data.last_import.error_code ? ` (${status.data.last_import.error_code})` : ''}.
            This view continues to use the retained stored snapshot.
          </div>
        )}
        <>
          {loading && <DataLoading view={view} cutoff={filters.cutoff} />}
          {!loading && error && (
            <section className="card data-state" role="alert">
              <h2>
                {staleSnapshot
                  ? 'Selected snapshot unavailable'
                  : error.code === 'alignment_unverified'
                    ? 'Comparison policy not confirmed'
                    : error.code === 'dataset_unavailable'
                      ? 'Dataset unavailable'
                      : 'Data request failed'}
              </h2>
              <p>{error.message}</p>
              {staleSnapshot ? (
                <>
                  <p>
                    The pinned snapshot was not found. Select the active snapshot to continue;
                    exports remain disabled.
                  </p>
                  <button
                    className="button primary"
                    type="button"
                    onClick={workspace.useActiveSnapshot}
                  >
                    Use active snapshot
                  </button>
                </>
              ) : (
                <button className="button" type="button" onClick={retry}>
                  Retry data request
                </button>
              )}
              {error.code === 'alignment_unverified' && (
                <p>
                  Forecast exploration remains available in Decision view. Accuracy waits for a
                  documented comparison policy.
                </p>
              )}
              <button className="text-button" type="button" onClick={openDetails}>
                Inspect data details
              </button>
            </section>
          )}
          {!loading && !error && status.data && !snapshot && (
            <section className="card data-state" role="status">
              <h2>No stored dataset</h2>
              <p>
                Import a dataset with the separate command-line tool, then refresh. The browser
                reads stored snapshots and does not download Elexon data.
              </p>
              <p>
                See the README for fixture and live import commands. Synthetic fixtures are labelled
                when loaded.
              </p>
              {status.data.last_import?.status === 'failed' && (
                <p>
                  Last import failed
                  {status.data.last_import.error_code
                    ? `: ${status.data.last_import.error_code}`
                    : ''}
                  . Any prior snapshot is retained.
                </p>
              )}
              <button className="button primary" type="button" onClick={status.retry}>
                Refresh dataset status
              </button>
              <button className="text-button" type="button" onClick={openDetails}>
                Inspect data details
              </button>
            </section>
          )}
          {data && (
            <>
              <DataOverview view={view} data={data} onOpenDetails={openDetails} />
              <DataTables key={`${filterKey}-${data.meta.snapshot_id}`} view={view} data={data} />
            </>
          )}
        </>
        <p className="sr-only" role="status" aria-live="polite">
          {workspace.announcement}
        </p>
      </Layout>
      {detailsOpen && (
        <DataDetails
          onClose={closeDetails}
          status={status.data}
          statusError={status.error?.message}
          onRetry={status.retry}
        />
      )}
    </>
  )
}
