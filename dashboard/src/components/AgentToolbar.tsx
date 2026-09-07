import { memo } from 'react'
import type { AgentFilter } from '../utils/agents'
import styles from './Components.module.css'

interface AgentToolbarProps {
  query: string
  filter: AgentFilter
  onQueryChange: (value: string) => void
  onFilterChange: (value: AgentFilter) => void
}

const filters: { id: AgentFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'online', label: 'Online' },
  { id: 'offline', label: 'Offline' },
  { id: 'warning', label: 'Warning' },
]

export const AgentToolbar = memo(function AgentToolbar({
  query,
  filter,
  onQueryChange,
  onFilterChange,
}: AgentToolbarProps) {
  return (
    <section className={styles.toolbar} aria-label="Agent search and filters">
      <label className={styles.searchLabel} htmlFor="agent-search">
        Search agents
        <input
          className={styles.searchInput}
          id="agent-search"
          type="search"
          value={query}
          placeholder="Search name, hostname, OS, or status"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>
      <div className={styles.filterGroup} role="group" aria-label="Agent status filters">
        {filters.map((item) => (
          <button
            className={`${styles.filterButton} ${filter === item.id ? styles.filterActive : ''}`}
            key={item.id}
            type="button"
            aria-pressed={filter === item.id}
            onClick={() => onFilterChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  )
})
