import { useRef, useState, type FormEvent } from 'react'
import { validateFilters, type FilterErrors } from '../state'
import { formatDate, nextDay, type Filters as FilterValues, type View } from '../types'

interface Props {
  view: View
  filters: FilterValues
  onApply: (filters: FilterValues) => void
}

export function Filters({ view, filters, onApply }: Props) {
  const [draft, setDraft] = useState(filters)
  const [errors, setErrors] = useState<FilterErrors>({})
  const form = useRef<HTMLFormElement>(null)
  const accuracy = view === 'accuracy'
  const delivery = accuracy
    ? `${formatDate(nextDay(filters.decisionFrom))} – ${formatDate(nextDay(filters.decisionTo))}`
    : formatDate(nextDay(filters.decisionFrom))
  const pending =
    draft.decisionFrom !== filters.decisionFrom ||
    draft.cutoff !== filters.cutoff ||
    (accuracy && draft.decisionTo !== filters.decisionTo)

  function change(key: keyof FilterValues, value: string) {
    setDraft((previous) => ({ ...previous, [key]: value }))
    setErrors((previous) => ({ ...previous, [key]: undefined }))
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const found = validateFilters(draft, view)
    setErrors(found)
    if (Object.keys(found).length) {
      const first = Object.keys(found)[0]
      form.current?.querySelector<HTMLInputElement>(`[name="${first}"]`)?.focus()
      return
    }
    onApply({ ...draft, decisionTo: accuracy ? draft.decisionTo : draft.decisionFrom })
  }

  return (
    <>
      <form
        className="filter-panel"
        aria-label="Historical decision filters"
        onSubmit={submit}
        noValidate
        ref={form}
      >
        <div className="field">
          <label htmlFor="decision-from">{accuracy ? 'Decision from' : 'Decision date'}</label>
          <input
            id="decision-from"
            name="decisionFrom"
            type="date"
            min="2026-01-01"
            max="2026-01-31"
            value={draft.decisionFrom}
            onChange={(event) => change('decisionFrom', event.target.value)}
            aria-invalid={!!errors.decisionFrom}
            aria-describedby={errors.decisionFrom ? 'from-error' : undefined}
            required
          />
          {errors.decisionFrom && (
            <span className="field-error" id="from-error">
              {errors.decisionFrom}
            </span>
          )}
        </div>
        {accuracy && (
          <div className="field">
            <label htmlFor="decision-to">Decision to</label>
            <input
              id="decision-to"
              name="decisionTo"
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={draft.decisionTo}
              onChange={(event) => change('decisionTo', event.target.value)}
              aria-invalid={!!errors.decisionTo}
              aria-describedby={errors.decisionTo ? 'to-error' : undefined}
              required
            />
            {errors.decisionTo && (
              <span className="field-error" id="to-error">
                {errors.decisionTo}
              </span>
            )}
          </div>
        )}
        <div className="field cutoff">
          <label htmlFor="cutoff">Buying cutoff · UK time</label>
          <input
            id="cutoff"
            name="cutoff"
            type="time"
            step="60"
            value={draft.cutoff}
            onChange={(event) => change('cutoff', event.target.value)}
            aria-invalid={!!errors.cutoff}
            aria-describedby={errors.cutoff ? 'cutoff-error' : undefined}
            required
          />
          {errors.cutoff && (
            <span className="field-error" id="cutoff-error">
              {errors.cutoff}
            </span>
          )}
        </div>
        <div className="delivery-field">
          <span className="field-label">{accuracy ? 'Delivery period' : 'Delivery day'}</span>
          <strong>{delivery}</strong>
        </div>
        <button type="submit" className="button primary filter-action">
          Apply filters <span aria-hidden="true">→</span>
        </button>
      </form>
      {pending && (
        <p className="draft-note" role="status">
          You have unapplied changes. Apply to update the data view.
        </p>
      )}
    </>
  )
}
