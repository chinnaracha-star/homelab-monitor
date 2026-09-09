import { memo, type ReactNode } from 'react'
import type { IconName } from './Icon'
import { Icon } from './Icon'
import styles from './Components.module.css'

export const StatCard = memo(function StatCard({
  label,
  value,
  valueLabel,
  tone,
  icon,
}: {
  label: string
  value: number | string | ReactNode
  valueLabel?: string
  tone?: string
  icon?: IconName
}) {
  const isPlain = typeof value === 'number' || typeof value === 'string'
  const display = typeof value === 'number' ? value.toLocaleString() : value
  const ariaValue = valueLabel ?? (isPlain ? String(display) : '')
  const ariaLabel = ariaValue ? `${label} ${ariaValue}` : label

  return (
    <article className={styles.statCard} data-tone={tone} aria-label={ariaLabel}>
      <p className={styles.statLabel}>
        {icon ? <Icon name={icon} /> : null}
        {label}
      </p>
      <p className={`${styles.statValue} ${isPlain ? '' : styles.statValueRich}`.trim()}>
        <span className={styles.valuePulse} key={isPlain ? String(display) : valueLabel ?? label}>
          {display}
        </span>
      </p>
    </article>
  )
})
