import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Filters } from './components/Filters'
import { defaults } from './types'

describe('stored-data filter form', () => {
  it('keeps draft dates separate until a valid apply', () => {
    const apply = vi.fn()
    render(<Filters view="decision" filters={defaults.decision} onApply={apply} />)

    fireEvent.change(screen.getByLabelText('Decision date'), { target: { value: '2026-01-31' } })

    expect(apply).not.toHaveBeenCalled()
    expect(screen.getByText('16 Jan 2026')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(/unapplied changes/i)
    fireEvent.click(screen.getByRole('button', { name: /Apply filters/i }))
    expect(apply).toHaveBeenCalledWith({
      decisionFrom: '2026-01-31',
      decisionTo: '2026-01-31',
      cutoff: '09:30',
    })
  })

  it('shows a field error and focuses an unsupported decision date', () => {
    const apply = vi.fn()
    render(<Filters view="decision" filters={defaults.decision} onApply={apply} />)
    const date = screen.getByLabelText('Decision date')

    fireEvent.change(date, { target: { value: '2026-02-01' } })
    fireEvent.click(screen.getByRole('button', { name: /Apply filters/i }))

    expect(apply).not.toHaveBeenCalled()
    expect(date).toHaveAttribute('aria-invalid', 'true')
    expect(date).toHaveFocus()
    expect(
      screen.getByText('Choose a decision date from 1 to 31 January 2026.'),
    ).toBeInTheDocument()
  })

  it('blocks reversed accuracy ranges', () => {
    const apply = vi.fn()
    render(<Filters view="accuracy" filters={defaults.accuracy} onApply={apply} />)
    fireEvent.change(screen.getByLabelText('Decision from'), { target: { value: '2026-01-31' } })
    fireEvent.change(screen.getByLabelText('Decision to'), { target: { value: '2026-01-30' } })
    fireEvent.click(screen.getByRole('button', { name: /Apply filters/i }))

    expect(apply).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Decision to')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Choose an end date on or after the start date.')).toBeInTheDocument()
  })

  it('requires a cutoff and exposes next-month delivery labels', () => {
    const apply = vi.fn()
    render(
      <Filters
        view="decision"
        filters={{ ...defaults.decision, decisionFrom: '2026-01-31', decisionTo: '2026-01-31' }}
        onApply={apply}
      />,
    )
    expect(screen.getByText('01 Feb 2026')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Buying cutoff/), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /Apply filters/i }))
    expect(screen.getByText('Enter a buying cutoff in HH:MM format.')).toBeInTheDocument()
    expect(apply).not.toHaveBeenCalled()
  })
})
