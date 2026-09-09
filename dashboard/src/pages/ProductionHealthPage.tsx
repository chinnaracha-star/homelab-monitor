import { memo } from 'react'
import { getProductionHealthOverview } from '../api/dashboard'
import { EmptyState } from '../components/EmptyState'
import { LastUpdated } from '../components/LastUpdated'
import { OverviewSkeleton } from '../components/Skeleton'
import { SectionError } from '../components/SectionError'
import { StatusBadge } from '../components/StatusBadge'
import { LIVE_PAGE_POLL } from '../constants'
import { useLivePolling } from '../hooks/useDashboardSocket'
import type { ProductionHealthCheck } from '../types/dashboard'
import { formatBytes } from '../utils/bytes'
import { formatThaiDateTime } from '../utils/thaiDate'
import pageStyles from './Pages.module.css'
import styles from './ProductionHealthPage.module.css'

const EVENTS = ['overview_updated', 'agent_updated', 'alert_updated'] as const

function value(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'Unavailable' : String(value)
}

function timestamp(input: string | null): string {
  return input ? formatThaiDateTime(input, false) : 'Never'
}

const HealthCard = memo(function HealthCard({ check }: { check: ProductionHealthCheck }) {
  return (
    <article className={styles.healthCard} aria-label={`${check.component} ${check.status}`}>
      <header className={styles.healthHeader}>
        <h2>{check.component}</h2>
        <StatusBadge kind="service" status={check.status} />
      </header>
      <p className={styles.meta}>{check.message}</p>
      <p className={styles.meta}>Last check {formatThaiDateTime(check.last_check, false)}</p>
      {check.latency_ms !== null ? <p className={styles.meta}>Latency {check.latency_ms} ms</p> : null}
      {check.warning ? <p className={styles.meta}>Warning: {check.warning}</p> : null}
      {check.error ? <p className={styles.meta}>Error: {check.error}</p> : null}
    </article>
  )
})

export const ProductionHealthPage = memo(function ProductionHealthPage() {
  const snapshot = useLivePolling(getProductionHealthOverview, EVENTS, LIVE_PAGE_POLL)
  const data = snapshot.data
  const unhealthy = data?.health.checks.filter((check) =>
    ['warning', 'critical'].includes(check.status),
  ) ?? []

  return (
    <section className={pageStyles.page}>
      <header className={pageStyles.pageHeader}>
        <div>
          <p className={pageStyles.eyebrow}>Mission Control</p>
          <h1 className={pageStyles.title}>Production Health</h1>
          <p className={pageStyles.description}>
            Live component health, host runtime details, and actionable diagnostics.
          </p>
        </div>
        <LastUpdated refreshing={snapshot.isRefreshing} value={snapshot.lastUpdated} />
      </header>

      {snapshot.error ? <SectionError title="Production health failed" onRetry={snapshot.retry} /> : null}
      {!data && !snapshot.error ? <OverviewSkeleton /> : null}
      {data ? (
        <>
          <article className={styles.scoreCard} aria-label={`Production health score ${data.health.score}`}>
            <div>
              <p className={pageStyles.eyebrow}>Production Health Score</p>
              <p className={styles.score}>{data.health.score}</p>
              <p className={styles.scoreLabel}>{data.health.status.toUpperCase()}</p>
            </div>
            <StatusBadge kind="service" status={data.health.status === 'excellent' ? 'healthy' : data.health.status} />
          </article>

          <section className={styles.healthGrid} aria-label="Production component health">
            {data.health.checks.map((check) => <HealthCard check={check} key={check.component} />)}
          </section>

          <section className={pageStyles.section} aria-labelledby="runtime-title">
            <h2 className={styles.sectionTitle} id="runtime-title">Runtime</h2>
            <div className={styles.detailsGrid}>
              <DetailCard title="Agent" rows={[
                ['Running', data.runtime.agent.state],
                ['Restart Count', value(data.runtime.agent.restart_count)],
                ['Last Heartbeat', timestamp(data.runtime.agent.last_heartbeat)],
                ['Last Report', timestamp(data.runtime.agent.last_report)],
                ['Last Metrics Upload', timestamp(data.runtime.agent.last_metrics_upload)],
              ]} />
              <DetailCard title="Telegram" rows={[
                ['Bot Connected', data.runtime.telegram.bot_connected === null ? 'Unknown' : data.runtime.telegram.bot_connected ? 'Yes' : 'No'],
                ['Last Successful Send', timestamp(data.runtime.telegram.last_successful_send)],
                ['Last Failed Send', timestamp(data.runtime.telegram.last_failed_send)],
                ['Failure Reason', value(data.runtime.telegram.failure_reason)],
                ['Retry Queue', data.runtime.telegram.retry_queue],
              ]} />
              <DetailCard title="Tailscale" rows={[
                ['Connected', data.runtime.tailscale.connected ? 'Yes' : 'No'],
                ['Tailnet', value(data.runtime.tailscale.tailnet)],
                ['MagicDNS', data.runtime.tailscale.magic_dns === null ? 'Unknown' : data.runtime.tailscale.magic_dns ? 'Enabled' : 'Disabled'],
                ['Relay / Direct', value(data.runtime.tailscale.connection_type)],
                ['Exit Node', value(data.runtime.tailscale.exit_node)],
                ['Remote Access URL', value(data.runtime.tailscale.remote_access_url)],
              ]} />
            </div>
          </section>

          <section className={pageStyles.section} aria-labelledby="docker-title">
            <h2 className={styles.sectionTitle} id="docker-title">Docker</h2>
            {!data.runtime.docker_available ? <EmptyState message="Docker is unavailable to the API process." /> : null}
            {data.runtime.docker_available && data.runtime.containers.length === 0 ? <EmptyState message="Docker is available, but no containers were found." /> : null}
            {data.runtime.containers.length > 0 ? (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead><tr><th>Container</th><th>Status</th><th>Health</th><th>Restart Count</th><th>Image</th><th>Running Since</th></tr></thead>
                  <tbody>{data.runtime.containers.map((container) => (
                    <tr key={container.container}>
                      <td>{container.container}</td><td>{container.status}</td><td>{container.health}</td>
                      <td>{value(container.restart_count)}</td><td>{container.image}</td><td>{value(container.running_since)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : null}
          </section>

          <section className={pageStyles.section} aria-labelledby="resources-title">
            <h2 className={styles.sectionTitle} id="resources-title">Storage and Network</h2>
            <div className={styles.detailsGrid}>
              <DetailCard title="Storage" rows={[
                ['Disk Usage', data.storage.disk_usage_percent === null ? 'Unavailable' : `${data.storage.disk_usage_percent}%`],
                ['Free Space', data.storage.free_space_bytes === null ? 'Unavailable' : formatBytes(data.storage.free_space_bytes)],
                ['Filesystem', value(data.storage.filesystem)],
                ['Database Size', data.storage.database_size_bytes === null ? 'Unavailable' : formatBytes(data.storage.database_size_bytes)],
                ['Log Size', data.storage.log_size_bytes === null ? 'Unavailable' : formatBytes(data.storage.log_size_bytes)],
                ['Disk Read', data.storage.disk_read_bytes === null ? 'Unavailable' : formatBytes(data.storage.disk_read_bytes)],
                ['Disk Write', data.storage.disk_write_bytes === null ? 'Unavailable' : formatBytes(data.storage.disk_write_bytes)],
                ['IO Wait', data.storage.io_wait_percent === null ? 'Unavailable' : `${data.storage.io_wait_percent}%`],
              ]} />
              <DetailCard title="Network" rows={[
                ['LAN IP', value(data.network.lan_ip)],
                ['Tailscale IP', value(data.network.tailscale_ip)],
                ['Gateway', value(data.network.gateway)],
                ['Internet', data.network.internet],
                ['Latency', data.network.latency_ms === null ? 'Unavailable' : `${data.network.latency_ms} ms`],
                ['DNS', data.network.dns],
                ['Upload', data.network.upload_bytes === null ? 'Unavailable' : formatBytes(data.network.upload_bytes)],
                ['Download', data.network.download_bytes === null ? 'Unavailable' : formatBytes(data.network.download_bytes)],
                ['Network Errors', value(data.network.network_errors)],
              ]} />
            </div>
          </section>

          <section className={pageStyles.section} aria-labelledby="diagnostics-title">
            <h2 className={styles.sectionTitle} id="diagnostics-title">Auto Diagnostics</h2>
            {unhealthy.length === 0 ? <EmptyState message="No unhealthy components require action." /> : (
              <div className={styles.diagnostics}>
                {unhealthy.map((check) => (
                  <article className={styles.diagnostic} key={check.component}>
                    <h3>{check.component}: {check.message}</h3>
                    <p><strong>Possible Cause:</strong> {check.possible_cause ?? 'No cause available.'}</p>
                    <p><strong>Recommended Action:</strong> {check.recommended_action ?? 'Review service logs.'}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </section>
  )
})

function DetailCard({ title, rows }: { title: string; rows: (string | number)[][] }) {
  return (
    <article className={styles.detailCard}>
      <h3>{title}</h3>
      <dl className={styles.detailList}>
        {rows.map(([label, rowValue]) => <div key={label}><dt>{label}</dt><dd>{rowValue}</dd></div>)}
      </dl>
    </article>
  )
}
