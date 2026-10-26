import { Icon } from './Icon'

export function ScopeNote({ cutoff }: { cutoff: string }) {
  return (
    <div className="scope-note">
      <span>
        <Icon name="info" />
        Applied cutoff: {cutoff} UK · Demo default: 09:30 UK.
      </span>
      <span>All displayed times: Europe/London · power in MW</span>
    </div>
  )
}
