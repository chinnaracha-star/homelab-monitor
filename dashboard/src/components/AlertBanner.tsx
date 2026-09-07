import { memo } from 'react'
import { Link } from 'react-router-dom'
import { getActiveAlerts } from '../api/dashboard'
import { usePolling } from '../hooks/usePolling'
import { alertLabels } from '../utils/metrics'
import styles from './Components.module.css'

export const AlertBanner = memo(function AlertBanner() {
  const { data: alerts } = usePolling(getActiveAlerts)

  if (!alerts || alerts.length === 0) {
    return null
  }

  const preview = alerts[0]

  return (
    <Link className={styles.alertBanner} to="/alerts" aria-label="View active alerts">
      <strong className={styles.alertTitle}>
        ⚠ Active Alerts ({alerts.length})
      </strong>
      <span className={styles.alertPreview}>
        <span>{alertLabels[preview.kind] ?? preview.kind}</span>
        <span>{preview.agent_name}</span>
      </span>
    </Link>
  )
})
