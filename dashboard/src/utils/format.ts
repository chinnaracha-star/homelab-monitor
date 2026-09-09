import { formatThaiDateTime, formatThaiTime } from './thaiDate'

export { formatThaiDate, formatThaiDateTime, formatThaiTime } from './thaiDate'

export function formatDateTime(value: string | null): string {
  if (!value) {
    return 'Never'
  }
  const formatted = formatThaiDateTime(value)
  return formatted === '—' ? 'Unknown' : formatted
}

export function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    return 'Unavailable'
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let amount = value
  let unitIndex = 0

  while (amount >= 1024 && unitIndex < units.length - 1) {
    amount /= 1024
    unitIndex += 1
  }

  const precision = amount >= 10 || unitIndex === 0 ? 0 : 1
  return `${amount.toFixed(precision)} ${units[unitIndex]}`
}

export function formatClock(value: Date): string {
  return formatThaiTime(value)
}

export function formatUptime(value: number | undefined): string {
  if (value === undefined || value < 0) {
    return 'Unavailable'
  }

  const days = Math.floor(value / 86_400)
  const hours = Math.floor((value % 86_400) / 3_600)
  const minutes = Math.floor((value % 3_600) / 60)

  return [days ? `${days}d` : '', hours ? `${hours}h` : '', `${minutes}m`]
    .filter(Boolean)
    .join(' ')
}
