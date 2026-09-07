export function formatRelativeTime(value: string | null, now: number): string {
  if (!value) {
    return 'Never'
  }

  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) {
    return 'Unknown'
  }

  const seconds = Math.max(0, Math.floor((now - timestamp) / 1_000))
  if (seconds < 60) {
    return `${seconds} sec ago`
  }

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes} min ago`
  }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  }

  const days = Math.floor(hours / 24)
  return days === 1 ? '1 day ago' : `${days} days ago`
}
