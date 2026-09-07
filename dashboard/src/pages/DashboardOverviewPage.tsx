import { useMemo } from 'react'
import { getActiveAlerts, getAgents, getDashboardOverview } from '../api/dashboard'
import { ConnectionLost } from '../components/ConnectionLost'
import { LastUpdated } from '../components/LastUpdated'
import { OverviewSkeleton } from '../components/Skeleton'
import { SectionError } from '../components/SectionError'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import { usePolling } from '../hooks/usePolling'
import styles from './Pages.module.css'

export function DashboardOverviewPage() {
  const overview = usePolling(getDashboardOverview)
  const agents = usePolling(getAgents)
  const alerts = usePolling(getActiveAlerts)

  const isRefreshing = overview.isRefreshing || agents.isRefreshing || alerts.isRefreshing
  const lastUpdated = [overview.lastUpdated, agents.lastUpdated, alerts.lastUpdated]
    .filter((value): value is Date => value !== null)
    .sort((left, right) => right.getTime() - left.getTime())[0] ?? null

  const warningCount = useMemo(() => {
    if (!agents.data || !alerts.data) {
      return 0
    }
    const agentsWithAlerts = new Set(alerts.data.map((alert) => alert.agent_id))
    return agents.data.filter(
      (agent) => agent.status !== 'offline' && agentsWithAlerts.has(agent.id),
    ).length
  }, [agents.data, alerts.data])

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>System overview</p>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.description}>Current monitoring coverage at a glance.</p>
        </div>
        <LastUpdated refreshing={isRefreshing} value={lastUpdated} />
      </header>

      <section className={styles.section} aria-labelledby="overview-summary-title">
        <h2 className={styles.sectionTitle} id="overview-summary-title">
          Summary
        </h2>
        {overview.error ? (
          <SectionError
            title="Overview API failed"
            message="Summary cards could not be loaded."
            onRetry={overview.retry}
          />
        ) : null}
        {!overview.data && !overview.error ? <OverviewSkeleton /> : null}
        {overview.data ? (
          <section className={styles.statGrid} aria-label="Monitoring summary">
            <StatCard label="Total Agents" value={overview.data.agents.total} />
            <StatCard label="Online" value={overview.data.agents.online} />
            <StatCard label="Offline" value={overview.data.agents.offline} />
            <StatCard label="Total Reports" value={overview.data.reports.total} />
          </section>
        ) : null}
      </section>

      <section className={styles.section} aria-labelledby="overview-agents-title">
        <h2 className={styles.sectionTitle} id="overview-agents-title">
          Agents
        </h2>
        {agents.error ? (
          <SectionError title="Agents API failed" onRetry={agents.retry} />
        ) : null}
        {agents.data ? (
          <article className={styles.infoPanel} aria-label="Agent status snapshot">
            <div className={styles.infoItem}>
              <p className={styles.infoLabel}>Registered</p>
              <p className={styles.infoValue}>{agents.data.length}</p>
            </div>
            <div className={styles.infoItem}>
              <p className={styles.infoLabel}>Warning</p>
              <p className={styles.infoValue}>{warningCount}</p>
            </div>
            <div className={styles.infoItem}>
              <p className={styles.infoLabel}>Statuses</p>
              <p className={styles.infoValue}>
                {agents.data.slice(0, 4).map((agent) => (
                  <StatusBadge key={agent.id} status={agent.status} />
                ))}
              </p>
            </div>
          </article>
        ) : null}
      </section>

      <section className={styles.section} aria-labelledby="overview-alerts-title">
        <h2 className={styles.sectionTitle} id="overview-alerts-title">
          Alerts
        </h2>
        {alerts.error ? (
          <SectionError title="Alerts API failed" onRetry={alerts.retry} />
        ) : null}
        {alerts.data ? (
          <article className={styles.infoPanel} aria-label="Active alert snapshot">
            <div className={styles.infoItem}>
              <p className={styles.infoLabel}>Active</p>
              <p className={styles.infoValue}>{alerts.data.length}</p>
            </div>
            <div className={styles.infoItem}>
              <p className={styles.infoLabel}>Latest</p>
              <p className={styles.infoValue}>
                {alerts.data[0] ? `${alerts.data[0].kind} · ${alerts.data[0].agent_name}` : 'None'}
              </p>
            </div>
          </article>
        ) : null}
      </section>

      {overview.error && agents.error && alerts.error ? (
        <ConnectionLost
          onRetry={() => {
            overview.retry()
            agents.retry()
            alerts.retry()
          }}
        />
      ) : null}
    </section>
  )
}
