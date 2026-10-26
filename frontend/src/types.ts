export type View = 'decision' | 'accuracy'
export interface Filters {
  decisionFrom: string
  decisionTo: string
  cutoff: string
}

export const defaults: Record<View, Filters> = {
  decision: { decisionFrom: '2026-01-15', decisionTo: '2026-01-15', cutoff: '09:30' },
  accuracy: { decisionFrom: '2026-01-01', decisionTo: '2026-01-31', cutoff: '09:30' },
}

// UI calendar labels only. Analytical grids and cutoff selection belong to Python.
export function nextDay(value: string): string {
  const day = new Date(`${value}T12:00:00Z`)
  day.setUTCDate(day.getUTCDate() + 1)
  return day.toISOString().slice(0, 10)
}

const formatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Europe/London',
})
export function formatDate(value: string): string {
  return formatter.format(new Date(`${value}T12:00:00Z`))
}
