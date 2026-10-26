import type { ReactNode } from 'react'

type Name = 'chart' | 'accuracy' | 'info' | 'download' | 'arrow' | 'warning' | 'data'

const paths: Record<Name, ReactNode> = {
  chart: <path d="M4 4v16h16M7 14l4-4 4 2 5-7" />,
  accuracy: <path d="M4 12h16M6 7v10M12 4v16M18 8v8" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7h.01" />
    </>
  ),
  download: <path d="M12 3v12m-4-4 4 4 4-4M5 16v4h14v-4" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  warning: <path d="m12 3 10 18H2L12 3ZM12 9v5M12 17h.01" />,
  data: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0" />
    </>
  ),
}

export function Icon({ name, className = '' }: { name: Name; className?: string }) {
  return (
    <svg className={`icon ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}
