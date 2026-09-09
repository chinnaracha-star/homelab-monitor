import { memo, useMemo } from 'react'
import { getActiveAlerts, getAgents, getBackupStatus, getDashboardOverview } from '../api/dashboard'
import { ConnectionLost } from '../components/ConnectionLost'
import { GroupCard } from '../components/GroupCard'
import { LastUpdated } from '../components/LastUpdated'
import { OfflineBanner } from '../components/OfflineBanner'
import { OverviewSkeleton } from '../components/Skeleton'
import { PwaInstallButton } from '../components/PwaInstallButton'
import { SectionError } from '../components/SectionError'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import { LIVE_PAGE_POLL } from '../constants'
import { useLivePolling } from '../hooks/useDashboardSocket'
import { useOptionalPwa } from '../pwa/PwaProvider'
import { formatPercent } from '../utils/bytes'
import { formatThaiDateTime } from '../utils/thaiDate'
import styles from './Pages.module.css'
import groupStyles from './GroupsPage.module.css'

const OVERVIEW_EVENTS = ['overview_updated', 'agent_updated', 'alert_updated'] as const
const AGENT_EVENTS = ['overview_updated', 'agent_updated', 'alert_updated'] as const
const ALERT_EVENTS = ['overview_updated', 'agent_updated', 'alert_updated'] as const

export const DashboardOverviewPage = memo(function DashboardOverviewPage() {
  const overview = useLivePolling(getDashboardOverview, OVERVIEW_EVENTS, LIVE_PAGE_POLL)
  const agents = useLivePolling(getAgents, AGENT_EVENTS, LIVE_PAGE_POLL)
  const alerts = useLivePolling(getActiveAlerts, ALERT_EVENTS, LIVE_PAGE_POLL)
  const backup = useLivePolling(getBackupStatus, OVERVIEW_EVENTS, LIVE_PAGE_POLL)
  const pwa = useOptionalPwa()
  const cached =
    Boolean(overview.data && overview.error) ||
    Boolean(agents.data && agents.error) ||
    Boolean(alerts.data && alerts.error)
  const hasCachedShell = Boolean(overview.data || agents.data || alerts.data)

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
        <div className={styles.headerActions}>
          <LastUpdated refreshing={isRefreshing} value={lastUpdated} />
          <PwaInstallButton />
        </div>
      </header>

      {pwa?.offline || cached ? (
        <OfflineBanner lastUpdated={lastUpdated} cached={cached || Boolean(pwa?.offline && hasCachedShell)} />
      ) : null}

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
            <StatCard label="Total Groups" value={overview.data.groups.total} />
          </section>
        ) : null}
      </section>

      <section className={styles.section} aria-labelledby="overview-backup-title">
        <h2 className={styles.sectionTitle} id="overview-backup-title">
          Backup
        </h2>
        {backup.error ? (
          <SectionError title="Backup API failed" onRetry={backup.retry} />
        ) : null}
        {backup.data ? (
          <section className={styles.statGrid} aria-label="Backup summary">
            <article className={styles.infoItem} aria-label={`Backup ${backup.data.destination.model}`}>
              <p className={styles.infoLabel}>Backup</p>
              <p className={styles.infoValue}>{backup.data.destination.model || 'TS-253 Pro'}</p>
            </article>
            <article className={styles.infoItem} aria-label={`Healthy ${backup.data.backup_health || backup.data.status}`}>
              <p className={styles.infoLabel}>Healthy</p>
              <p className={styles.infoValue}>{backup.data.backup_health || backup.data.status}</p>
            </article>
            <article
              className={styles.infoItem}
              aria-label={`Last Backup ${backup.data.last_backup || 'unknown'}`}
            >
              <p className={styles.infoLabel}>Last Backup</p>
              <p className={styles.infoValue}>
                {backup.data.last_backup ? formatThaiDateTime(backup.data.last_backup, false) : 'unknown'}
              </p>
            </article>
            <article
              className={styles.infoItem}
              aria-label={`Running % ${formatPercent(backup.data.progress_percent)}`}
            >
              <p className={styles.infoLabel}>Running %</p>
              <p className={styles.infoValue}>{formatPercent(backup.data.progress_percent)}</p>
            </article>
          </section>
        ) : null}
      </section>

      {overview.data && overview.data.group_stats.length > 0 ? (
        <section className={styles.section} aria-labelledby="overview-groups-title">
          <h2 className={styles.sectionTitle} id="overview-groups-title">
            Groups
          </h2>
          <section className={groupStyles.groupGrid} aria-label="Agents and online counts per group">
            {overview.data.group_stats.map((group) => (
              <GroupCard
                group={{
                  id: group.id,
                  name: group.name,
                  description: '',
                  agents: group.agents,
                  online: group.online,
                  agent_ids: [],
                }}
                key={group.id}
              />
            ))}
          </section>
        </section>
      ) : null}

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

      {overview.error && agents.error && alerts.error && !hasCachedShell ? (
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
})
