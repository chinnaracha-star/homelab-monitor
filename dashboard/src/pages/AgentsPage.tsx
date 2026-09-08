import { memo, useCallback, useMemo, useState } from 'react'
import { getActiveAlerts, getAgents, getGroups, getLatestAgentReport } from '../api/dashboard'
import { AgentTable } from '../components/AgentTable'
import { AgentToolbar } from '../components/AgentToolbar'
import { LastUpdated } from '../components/LastUpdated'
import { SectionError } from '../components/SectionError'
import { TableSkeleton } from '../components/Skeleton'
import { useLivePolling } from '../hooks/useDashboardSocket'
import { useLocalStorage } from '../hooks/useLocalStorage'
import { useNow } from '../hooks/useNow'
import { AGENT_FILTER_STORAGE_KEY, isAgentFilter, type AgentFilter } from '../utils/agents'
import { isApiErrorCode } from '../utils/errors'
import { getSystemMetrics } from '../utils/metrics'
import styles from './Pages.module.css'

const AGENT_EVENTS = ['overview_updated', 'agent_updated'] as const
const ALERT_EVENTS = ['overview_updated', 'alert_updated'] as const

export const AgentsPage = memo(function AgentsPage() {
  const now = useNow()
  const [query, setQuery] = useState('')
  const [groupId, setGroupId] = useState('all')
  const [storedFilter, setStoredFilter] = useLocalStorage(AGENT_FILTER_STORAGE_KEY, 'all')
  const filter: AgentFilter = isAgentFilter(storedFilter) ? storedFilter : 'all'
  const agents = useLivePolling(getAgents, AGENT_EVENTS)
  const groups = useLivePolling(getGroups, AGENT_EVENTS)
  const alerts = useLivePolling(getActiveAlerts, ALERT_EVENTS)

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

  const osNames = useLivePolling(loadOsNames, AGENT_EVENTS, { enabled: Boolean(agents.data) })

  const alertCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const alert of alerts.data ?? []) {
      counts[alert.agent_id] = (counts[alert.agent_id] ?? 0) + 1
    }
    return counts
  }, [alerts.data])

  const visibleAgents = useMemo(() => {
    if (!agents.data) {
      return []
    }
    if (groupId === 'all') {
      return agents.data
    }
    const memberIds = new Set(groups.data?.find((group) => group.id === groupId)?.agent_ids ?? [])
    return agents.data.filter((agent) => memberIds.has(agent.id))
  }, [agents.data, groupId, groups.data])

  const isRefreshing = agents.isRefreshing || alerts.isRefreshing || osNames.isRefreshing || groups.isRefreshing
  const lastUpdated =
    [agents.lastUpdated, alerts.lastUpdated, osNames.lastUpdated, groups.lastUpdated]
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
        groups={groups.data ?? []}
        groupId={groupId}
        query={query}
        onFilterChange={(value) => setStoredFilter(value)}
        onGroupChange={setGroupId}
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
          agents={visibleAgents}
          alertCounts={alertCounts}
          filter={filter}
          now={now}
          osNames={osNames.data ?? {}}
          query={query}
        />
      ) : null}
    </section>
  )
})
