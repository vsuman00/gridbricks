import { validSnapshotId } from './apiValidation'
import { defaults, type Filters, type View } from './types'

export type FilterErrors = Partial<Record<keyof Filters, string>>
export interface WorkspaceQuery {
  view: View
  filters: Filters
  snapshotId: string | null
  hasDates: boolean
  warning: string | null
}

export function validateFilters(filters: Filters, view: View): FilterErrors {
  const errors: FilterErrors = {}
  const january = /^2026-01-(0[1-9]|[12]\d|3[01])$/
  if (!january.test(filters.decisionFrom)) {
    errors.decisionFrom = 'Choose a decision date from 1 to 31 January 2026.'
  }
  if (view === 'accuracy') {
    if (!january.test(filters.decisionTo)) {
      errors.decisionTo = 'Choose an end date from 1 to 31 January 2026.'
    } else if (!errors.decisionFrom && filters.decisionTo < filters.decisionFrom) {
      errors.decisionTo = 'Choose an end date on or after the start date.'
    }
  }
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(filters.cutoff)) {
    errors.cutoff = 'Enter a buying cutoff in HH:MM format.'
  }
  return errors
}

export function parseQuery(search: string): WorkspaceQuery {
  if (search.length > 2048) {
    return {
      view: 'decision',
      filters: { ...defaults.decision },
      snapshotId: null,
      hasDates: false,
      warning: 'This link is too long. January defaults are shown; no data was requested.',
    }
  }
  const params = new URLSearchParams(search)
  const view: View = params.get('view') === 'accuracy' ? 'accuracy' : 'decision'
  const from = params.get(view === 'decision' ? 'decision_date' : 'decision_from')
  const filters = {
    decisionFrom: from ?? defaults[view].decisionFrom,
    decisionTo:
      view === 'decision'
        ? (from ?? defaults.decision.decisionTo)
        : (params.get('decision_to') ?? defaults.accuracy.decisionTo),
    cutoff: params.get('cutoff') ?? defaults[view].cutoff,
  }
  const badView = params.has('view') && !['decision', 'accuracy'].includes(params.get('view')!)
  const badSnapshot = params.has('snapshot_id') && !validSnapshotId(params.get('snapshot_id'))
  const unsupported = params.has('mode') || params.has('preview')
  const duplicate = [...params.keys()].some((key) => params.getAll(key).length > 1)
  const invalid =
    Object.keys(validateFilters(filters, view)).length > 0 ||
    badView ||
    badSnapshot ||
    unsupported ||
    duplicate
  return {
    view,
    snapshotId: invalid ? null : params.get('snapshot_id'),
    hasDates: from !== null,
    filters: invalid ? { ...defaults[view] } : filters,
    warning: invalid
      ? 'This link contains invalid or unsupported filters. January defaults are shown; no data was requested.'
      : null,
  }
}

export function serializeQuery(view: View, filters: Filters, snapshotId?: string | null): string {
  const params = new URLSearchParams({ view })
  if (view === 'decision') params.set('decision_date', filters.decisionFrom)
  else {
    params.set('decision_from', filters.decisionFrom)
    params.set('decision_to', filters.decisionTo)
  }
  params.set('cutoff', filters.cutoff)
  if (snapshotId) params.set('snapshot_id', snapshotId)
  return `?${params.toString()}`
}
