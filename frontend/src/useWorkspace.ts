import { useEffect, useState } from 'react'
import { parseQuery, serializeQuery } from './state'
import { defaults, type Filters, type View } from './types'
import type { Snapshot } from './api'

export function useWorkspace() {
  const [workspace, setWorkspace] = useState(() => {
    const query = parseQuery(window.location.search)
    return {
      view: query.view,
      snapshotId: query.snapshotId ?? null,
      hasDates: query.hasDates ?? false,
      filtersByView: { ...defaults, [query.view]: query.filters },
      warning: query.warning,
      announcement: '',
    }
  })
  useEffect(() => {
    function restore() {
      const query = parseQuery(window.location.search)
      setWorkspace((previous) => ({
        ...previous,
        view: query.view,
        snapshotId: query.snapshotId ?? null,
        hasDates: query.hasDates ?? false,
        filtersByView: { ...previous.filtersByView, [query.view]: query.filters },
        warning: query.warning,
        announcement: 'Workspace restored from the link.',
      }))
    }
    window.addEventListener('popstate', restore)
    return () => window.removeEventListener('popstate', restore)
  }, [])
  function update(
    view: View,
    filters: Filters,
    announcement: string,
    snapshotId = workspace.snapshotId,
    replace = false,
  ) {
    const search = serializeQuery(view, filters, snapshotId)
    if (window.location.search !== search)
      window.history[replace ? 'replaceState' : 'pushState'](
        null,
        '',
        `${window.location.pathname}${search}`,
      )
    setWorkspace((previous) => ({
      ...previous,
      view,
      snapshotId,
      hasDates: true,
      filtersByView: { ...previous.filtersByView, [view]: filters },
      warning: null,
      announcement,
    }))
  }
  return {
    ...workspace,
    filters: workspace.filtersByView[workspace.view],
    selectView(view: View) {
      update(
        view,
        workspace.filtersByView[view],
        `${view === 'accuracy' ? 'Accuracy' : 'Decision'} view opened.`,
      )
    },
    applyFilters(filters: Filters) {
      update(workspace.view, filters, 'Applied filters updated.')
    },
    pinSnapshot(snapshot: Snapshot) {
      if (workspace.snapshotId) return
      const filters = { ...workspace.filtersByView[workspace.view] }
      if (!workspace.hasDates && /^2026-01-\d{2}$/.test(snapshot.decision_from)) {
        filters.decisionFrom = snapshot.decision_from
        filters.decisionTo =
          workspace.view === 'decision' ? snapshot.decision_from : snapshot.decision_to
      }
      update(workspace.view, filters, 'Stored snapshot selected.', snapshot.snapshot_id, true)
    },
    useActiveSnapshot() {
      update(
        workspace.view,
        workspace.filtersByView[workspace.view],
        'Checking the active snapshot.',
        null,
      )
    },
    resetLink() {
      update(workspace.view, { ...defaults[workspace.view] }, 'January defaults restored.')
    },
  }
}
