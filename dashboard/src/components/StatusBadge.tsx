import { memo } from 'react'
import { normalizeStatus } from '../utils/agents'
import styles from './Components.module.css'

interface StatusBadgeProps {
  status: string
  alertCount?: number
}

const labels: Record<string, string> = {
  online: 'Online',
  offline: 'Offline',
  warning: 'Warning',
  registered: 'Registered',
}

export const StatusBadge = memo(function StatusBadge({ status, alertCount = 0 }: StatusBadgeProps) {
  const displayStatus = normalizeStatus(status, alertCount)
  const label = labels[displayStatus] ?? status
  const countLabel = alertCount > 0 ? ` ${alertCount}` : ''

  return (
    <span
      className={`${styles.badge} ${styles[displayStatus] ?? styles.unknown}`}
      aria-label={`Status ${label}${alertCount > 0 ? `, ${alertCount} alerts` : ''}`}
    >
      {label}
      {countLabel ? <span className={styles.badgeCount}>{alertCount}</span> : null}
    </span>
  )
})
