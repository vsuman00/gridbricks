import { useEffect, useRef, type KeyboardEvent } from 'react'
import { useHealth } from '../useHealth'
import { timestamp, type DataStatus } from '../api'

export function DataDetails({
  onClose,
  status,
  statusError,
  onRetry,
}: {
  onClose: () => void
  status?: DataStatus
  statusError?: string
  onRetry?: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const { connection, retry } = useHealth()
  useEffect(() => {
    if (dialog.current && !dialog.current.open) dialog.current.showModal()
  }, [])

  const labels = {
    checking: 'Checking connection',
    connected: 'API connected',
    unavailable: 'API unavailable',
  }

  function trapFocus(event: KeyboardEvent<HTMLDialogElement>) {
    if (event.key !== 'Tab') return
    const controls = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), [tabindex="0"]',
      ),
    )
    const first = controls[0]
    const last = controls.at(-1)
    const active = document.activeElement
    if (active === event.currentTarget || (event.shiftKey ? active === first : active === last)) {
      event.preventDefault()
      const target = event.shiftKey ? last : first
      target?.focus()
    }
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="details-title"
      aria-describedby="details-description"
      onClose={onClose}
      onKeyDown={trapFocus}
    >
      <div className="dialog-heading">
        <div>
          <p className="eyebrow">Sources &amp; methodology</p>
          <h2 id="details-title">Data details</h2>
        </div>
        <button
          className="button icon-button"
          type="button"
          aria-label="Close data details"
          onClick={() => dialog.current?.close()}
        >
          ×
        </button>
      </div>
      <p id="details-description">
        {status?.snapshot
          ? 'This workspace reads an immutable stored snapshot. Browser requests do not download Elexon records.'
          : 'No stored dataset is available. Run the documented import command, then refresh the dataset status.'}
      </p>
      <dl className="metadata">
        <div>
          <dt>Forecast input</dt>
          <dd>Elexon WINDFOR</dd>
        </div>
        <div>
          <dt>Actual input</dt>
          <dd>FUELHH · WIND</dd>
        </div>
        <div>
          <dt>Snapshot</dt>
          <dd>{status?.snapshot?.snapshot_id ?? 'No dataset'}</dd>
        </div>
        <div>
          <dt>Retrieved at</dt>
          <dd>{timestamp(status?.snapshot?.retrieved_at)}</dd>
        </div>
        <div>
          <dt>Last import outcome</dt>
          <dd>
            {status?.last_import
              ? `${status.last_import.status}${status.last_import.error_code ? ` · ${status.last_import.error_code}` : ''}`
              : 'Not run'}
          </dd>
        </div>
        <div>
          <dt>Time zone</dt>
          <dd>Europe/London</dd>
        </div>
        <div>
          <dt>Selection policy</dt>
          <dd>
            {status?.snapshot?.policies.selection ??
              status?.snapshot?.policies.selection_policy ??
              'Unavailable'}
          </dd>
        </div>
        <div>
          <dt>Alignment policy</dt>
          <dd>{status?.alignment.policy ?? 'Pending source validation'}</dd>
        </div>
        <div>
          <dt>Actual reference</dt>
          <dd>
            {status?.snapshot?.policies.actual ??
              status?.snapshot?.policies.actual_policy ??
              'Unavailable'}
          </dd>
        </div>
        {status?.snapshot && (
          <>
            <div>
              <dt>Source mode</dt>
              <dd>
                {status.snapshot.source_mode === 'fixture'
                  ? 'Synthetic fixture'
                  : 'Live-source snapshot'}
              </dd>
            </div>
            <div>
              <dt>Decision bounds</dt>
              <dd>
                {status.snapshot.decision_from} to {status.snapshot.decision_to}
              </dd>
            </div>
            <div>
              <dt>Delivery bounds</dt>
              <dd>
                {status.snapshot.delivery_from} to {status.snapshot.delivery_to}
              </dd>
            </div>
            <div>
              <dt>Snapshot status</dt>
              <dd>{status.snapshot.status}</dd>
            </div>
            <div>
              <dt>Input hash</dt>
              <dd>
                <code>{status.snapshot.input_hash}</code>
              </dd>
            </div>
            {Object.entries(status.snapshot.policies)
              .filter(([name]) => !['selection_policy', 'actual_policy'].includes(name))
              .map(([name, value]) => (
                <div key={name}>
                  <dt>{name.replaceAll('_', ' ')}</dt>
                  <dd>{value ?? 'Unavailable'}</dd>
                </div>
              ))}
          </>
        )}
        {status?.last_import?.completed_at && (
          <div>
            <dt>Last import completed · UK</dt>
            <dd>{timestamp(status.last_import.completed_at)}</dd>
          </div>
        )}
      </dl>
      <section className="dataset-diagnostics">
        <h3>Dataset status</h3>
        <p role="status">
          {statusError ?? status?.alignment.message ?? 'Checking stored data status.'}
        </p>
        {status?.last_import?.counts && (
          <p>
            Last import:{' '}
            {Object.entries(status.last_import.counts)
              .map(([name, count]) => `${name.replaceAll('_', ' ')} ${count}`)
              .join(' · ')}
          </p>
        )}
        {status?.sources?.map((source) => (
          <p key={source.dataset}>
            {source.dataset}: <code>{source.url}</code>
          </p>
        ))}
        {onRetry && (
          <button type="button" className="button" onClick={onRetry}>
            Refresh dataset status
          </button>
        )}
      </section>
      <div className="aside-note">
        <strong>Keep the timestamps distinct</strong> Publication time describes the source record.
        The buying cutoff is a simulated decision deadline. Retrieval time records a later download.
        Browser requests read stored snapshots only.
      </div>
      <section className="connection-panel" aria-labelledby="connection-title">
        <h3 id="connection-title">Local API process</h3>
        <p className={`connection-status ${connection}`} role="status">
          {labels[connection]}
        </p>
        <p className="support-text">
          This checks the local API process only. A successful connection does not mean data has
          been imported or validated.
        </p>
        <button
          className="button"
          type="button"
          disabled={connection === 'checking'}
          onClick={retry}
        >
          Check connection
        </button>
      </section>
      <p className="support-text">
        National wind coverage follows Elexon's operational metering scope. This workspace does not
        recommend purchases or estimate financial savings.
      </p>
      <div className="dialog-actions">
        <button className="button primary" type="button" onClick={() => dialog.current?.close()}>
          Close
        </button>
      </div>
    </dialog>
  )
}
