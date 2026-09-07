import { useCallback, useMemo, useState } from 'react'
import { getActiveAlerts, getAgents, getLatestAgentReport } from '../api/dashboard'
import { AgentTable } from '../components/AgentTable'
import { AgentToolbar } from '../components/AgentToolbar'
import { LastUpdated } from '../components/LastUpdated'
import { SectionError } from '../components/SectionError'
import { TableSkeleton } from '../components/Skeleton'
import { useLocalStorage } from '../hooks/useLocalStorage'
import { useNow } from '../hooks/useNow'
import { usePolling } from '../hooks/usePolling'
import { AGENT_FILTER_STORAGE_KEY, isAgentFilter, type AgentFilter } from '../utils/agents'
import { isApiErrorCode } from '../utils/errors'
import { getSystemMetrics } from '../utils/metrics'
import styles from './Pages.module.css'

export function AgentsPage() {
  const now = useNow()
  const [query, setQuery] = useState('')
  const [storedFilter, setStoredFilter] = useLocalStorage(AGENT_FILTER_STORAGE_KEY, 'all')
  const filter: AgentFilter = isAgentFilter(storedFilter) ? storedFilter : 'all'
  const agents = usePolling(getAgents)
  const alerts = usePolling(getActiveAlerts)

  const loadOsNames = useCallback(async () => {
    const currentAgents = agents.data ?? []
    const entries = await Promise.all(
      currentAgents.map(async (agent) => {
        try {
          const report = await getLatestAgentReport(agent.id)
          return [agent.id, getSystemMetrics(report)?.os?.distribution ?? ''] as const
        } catch (error) {
          if (isApiErrorCode(error, 'latest_report_not_found') || isApiErrorCode(error, 'agent_not_found')) {
            return [agent.id, ''] as const
          }
          return [agent.id, ''] as const
        }
      }),
    )
    return Object.fromEntries(entries)
  }, [agents.data])

  const osNames = usePolling(loadOsNames, { enabled: Boolean(agents.data) })

  const alertCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const alert of alerts.data ?? []) {
      counts[alert.agent_id] = (counts[alert.agent_id] ?? 0) + 1
    }
    return counts
  }, [alerts.data])

  const isRefreshing = agents.isRefreshing || alerts.isRefreshing || osNames.isRefreshing
  const lastUpdated =
    [agents.lastUpdated, alerts.lastUpdated, osNames.lastUpdated]
      .filter((value): value is Date => value !== null)
      .sort((left, right) => right.getTime() - left.getTime())[0] ?? null

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Infrastructure</p>
          <h1 className={styles.title}>Agents</h1>
          <p className={styles.description}>Hosts reporting to HomeLab Monitor.</p>
        </div>
        <LastUpdated refreshing={isRefreshing} value={lastUpdated} />
      </header>

      <AgentToolbar
        filter={filter}
        query={query}
        onFilterChange={(value) => setStoredFilter(value)}
        onQueryChange={setQuery}
      />

      {agents.error ? (
        <SectionError title="Agents API failed" onRetry={agents.retry} />
      ) : null}
      {alerts.error ? (
        <SectionError title="Alerts API failed" message="Status badges will omit alert counts." onRetry={alerts.retry} />
      ) : null}
      {!agents.data && !agents.error ? <TableSkeleton /> : null}
      {agents.data ? (
        <AgentTable
          agents={agents.data}
          alertCounts={alertCounts}
          filter={filter}
          now={now}
          osNames={osNames.data ?? {}}
          query={query}
        />
      ) : null}
    </section>
  )
}
