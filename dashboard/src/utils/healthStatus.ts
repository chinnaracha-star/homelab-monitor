export type DashboardHealthStatus = 'Excellent' | 'Good' | 'Warning' | 'Critical'

export function dashboardHealthStatus(
  severities: string[],
  score: number | null | undefined,
): DashboardHealthStatus {
  const ranks = new Set(severities.map((item) => item.toLowerCase()))
  if (ranks.has('critical')) {
    return 'Critical'
  }
  if (ranks.has('warning')) {
    return 'Warning'
  }
  if (typeof score === 'number' && score >= 90) {
    return 'Excellent'
  }
  return 'Good'
}

export function estimatedFullLabel(days: number | null | undefined, growthPerDay: number): string {
  if (days == null || growthPerDay <= 0) {
    return 'Unknown'
  }
  return `${Math.round(days)} Days`
}
