import { memo } from 'react'
import styles from './Components.module.css'

interface StatCardProps {
  label: string
  value: number
}

export const StatCard = memo(function StatCard({ label, value }: StatCardProps) {
  return (
    <article className={styles.statCard} aria-label={`${label} ${value.toLocaleString()}`}>
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue}>
        <span className={styles.valuePulse} key={value}>
          {value.toLocaleString()}
        </span>
      </p>
    </article>
  )
})
