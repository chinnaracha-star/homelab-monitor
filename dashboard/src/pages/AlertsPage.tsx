import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getActiveAlerts } from '../api/dashboard'
import { LastUpdated } from '../components/LastUpdated'
import { RelativeTime } from '../components/RelativeTime'
import { SectionError } from '../components/SectionError'
import { TableSkeleton } from '../components/Skeleton'
import { useNow } from '../hooks/useNow'
import { usePolling } from '../hooks/usePolling'
import { alertLabels } from '../utils/metrics'
import componentStyles from '../components/Components.module.css'
import styles from './Pages.module.css'

export function AlertsPage() {
  const now = useNow()
  const [resolvedOpen, setResolvedOpen] = useState(false)
  const { data: alerts, error, isRefreshing, lastUpdated, retry } =
    usePolling(getActiveAlerts)

  const sortedAlerts = useMemo(
    () =>
      [...(alerts ?? [])].sort(
        (left, right) => Date.parse(right.opened_at) - Date.parse(left.opened_at),
      ),
    [alerts],
  )

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Notifications</p>
          <h1 className={styles.title}>Active alerts</h1>
          <p className={styles.description}>Current issues detected by the alert engine.</p>
        </div>
        <LastUpdated refreshing={isRefreshing} value={lastUpdated} />
      </header>

      {error ? <SectionError title="Alerts API failed" onRetry={retry} /> : null}
      {!alerts && !error ? <TableSkeleton /> : null}

      {sortedAlerts.length > 0 ? (
        <ul className={componentStyles.alertList}>
          {sortedAlerts.map((alert) => (
            <li key={alert.id}>
              <Link
                className={componentStyles.alertItem}
                to={`/agents/${alert.agent_id}`}
                aria-label={`${alertLabels[alert.kind] ?? alert.kind} on ${alert.agent_name}`}
              >
                <span className={componentStyles.alertKind}>
                  {alertLabels[alert.kind] ?? alert.kind}
                </span>
                <span className={componentStyles.alertAgent}>{alert.agent_name}</span>
                <span
                  className={`${componentStyles.severityBadge} ${componentStyles[alert.severity] ?? componentStyles.warning}`}
                >
                  {alert.severity}
                </span>
                <span className={componentStyles.statusActive}>Active</span>
                <span className={componentStyles.alertAgent}>
                  Opened <RelativeTime now={now} value={alert.opened_at} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      {alerts && sortedAlerts.length === 0 && !error ? (
        <p className={styles.reportMeta}>No active alerts.</p>
      ) : null}

      <details
        className={styles.resolvedGroup}
        open={resolvedOpen}
        onToggle={(event) => setResolvedOpen(event.currentTarget.open)}
      >
        <summary>Resolved (0)</summary>
        <p className={styles.reportMeta}>
          Resolved alerts are not included in the current dashboard API.
        </p>
      </details>
    </section>
  )
}
