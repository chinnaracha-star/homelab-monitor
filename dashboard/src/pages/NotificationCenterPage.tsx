import { memo, useMemo, useState } from 'react'
import { getNotificationCenterStatistics, getNotificationHistory } from '../api/dashboard'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { LastUpdated } from '../components/LastUpdated'
import { OverviewSkeleton, TableSkeleton } from '../components/Skeleton'
import { RelativeTime } from '../components/RelativeTime'
import { SectionError } from '../components/SectionError'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import { useLivePolling } from '../hooks/useDashboardSocket'
import { useNow } from '../hooks/useNow'
import type { NotificationCenterItem } from '../types/dashboard'
import styles from './Pages.module.css'

const EVENTS = ['overview_updated', 'agent_updated', 'alert_updated'] as const

export const NotificationCenterPage = memo(function NotificationCenterPage() {
  const now = useNow()
  const history = useLivePolling(getNotificationHistory, EVENTS)
  const statistics = useLivePolling(getNotificationCenterStatistics, EVENTS)
  const [severity, setSeverity] = useState('all')
  const [source, setSource] = useState('all')
  const [readState, setReadState] = useState('all')
  const [agent, setAgent] = useState('all')
  const [date, setDate] = useState('')
  const items = useMemo(() => {
    return (history.data?.items ?? []).filter((item) => {
      if (severity !== 'all' && item.severity !== severity) {
        return false
      }
      if (source !== 'all' && item.source !== source) {
        return false
      }
      if (readState !== 'all' && item.read_state !== readState) {
        return false
      }
      if (agent !== 'all' && item.agent_id !== agent) {
        return false
      }
      if (date && !item.created_at.startsWith(date)) {
        return false
      }
      return true
    })
  }, [agent, date, history.data, readState, severity, source])
  const agents = useMemo(() => {
    const map = new Map<string, string>()
    for (const item of history.data?.items ?? []) {
      if (item.agent_id && item.agent_name) {
        map.set(item.agent_id, item.agent_name)
      }
    }
    return [...map.entries()]
  }, [history.data])
  const groups = useMemo(() => {
    const map = new Map<string, NotificationCenterItem[]>()
    for (const item of items) {
      const day = item.created_at.slice(0, 10)
      map.set(day, [...(map.get(day) ?? []), item])
    }
    return [...map.entries()]
  }, [items])
  const error = history.error || statistics.error
  const retry = () => {
    history.retry()
    statistics.retry()
  }

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Monitoring</p>
          <h1 className={styles.title}>Notification Center</h1>
          <p className={styles.description}>Read-only history of delivered notifications.</p>
        </div>
        <LastUpdated refreshing={history.isRefreshing} value={history.lastUpdated} />
      </header>
      {error ? <SectionError title="Notification center failed" onRetry={retry} /> : null}
      {!statistics.data && !error ? <OverviewSkeleton /> : null}
      {statistics.data ? (
        <section className={styles.statGrid} aria-label="Notification statistics">
          <StatCard label="Unread" value={statistics.data.unread} />
          <StatCard label="Today" value={statistics.data.today} />
          <StatCard label="This Week" value={statistics.data.this_week} />
          <StatCard label="Critical" value={statistics.data.critical} />
        </section>
      ) : null}
      <section className={styles.filterBar} aria-label="Notification filters">
        <p className={styles.filterField}>
          <label htmlFor="nc-severity">Severity</label>
          <select id="nc-severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="all">all</option>
            <option value="critical">critical</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
        </p>
        <p className={styles.filterField}>
          <label htmlFor="nc-source">Source</label>
          <select id="nc-source" value={source} onChange={(event) => setSource(event.target.value)}>
            <option value="all">all</option>
            <option value="telegram">telegram</option>
            <option value="discord">discord</option>
            <option value="slack">slack</option>
            <option value="email">email</option>
          </select>
        </p>
        <p className={styles.filterField}>
          <label htmlFor="nc-read">Read</label>
          <select id="nc-read" value={readState} onChange={(event) => setReadState(event.target.value)}>
            <option value="all">all</option>
            <option value="unread">unread</option>
            <option value="read">read</option>
          </select>
        </p>
        <p className={styles.filterField}>
          <label htmlFor="nc-agent">Agent</label>
          <select id="nc-agent" value={agent} onChange={(event) => setAgent(event.target.value)}>
            <option value="all">all</option>
            {agents.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </p>
        <p className={styles.filterField}>
          <label htmlFor="nc-date">Date</label>
          <input id="nc-date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </p>
      </section>
      {!history.data && !error ? <TableSkeleton label="Loading notifications" /> : null}
      {history.data && items.length === 0 ? <EmptyState message="No notifications yet." /> : null}
      {groups.map(([day, dayItems]) => (
        <section className={styles.section} key={day} aria-label={`Notifications ${day}`}>
          <h2 className={styles.sectionTitle}>{day}</h2>
          <ol className={styles.timelineList} aria-label="Notification timeline">
            {dayItems.map((item) => (
              <li className={styles.timelineItem} key={item.id}>
                <Icon name={item.kind === 'backup' ? 'backup' : 'notification'} />
                <StatusBadge kind="lifecycle" status={item.read_state === 'read' ? 'recovered' : 'active'} />
                <p className={styles.timelineKind}>{item.severity}</p>
                <p className={styles.timelineMessage}>{item.title}</p>
                <p className={styles.timelineTime}>{item.description}</p>
                <p className={styles.timelineTime}>
                  {item.agent_name ?? 'system'} · {item.source} · <RelativeTime now={now} value={item.created_at} />
                </p>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </section>
  )
})
