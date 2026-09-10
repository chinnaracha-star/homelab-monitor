import { describe, expect, it } from 'vitest'
import { dashboardHealthStatus, estimatedFullLabel } from './healthStatus'

describe('dashboard health and capacity labels', () => {
  it('maps alert severity to dashboard health', () => {
    expect(dashboardHealthStatus(['critical'], 99)).toBe('Critical')
    expect(dashboardHealthStatus(['warning'], 99)).toBe('Warning')
    expect(dashboardHealthStatus([], 94)).toBe('Excellent')
    expect(dashboardHealthStatus(['info'], 70)).toBe('Good')
  })

  it('formats estimated full without dividing by zero', () => {
    expect(estimatedFullLabel(138, 10)).toBe('138 Days')
    expect(estimatedFullLabel(5.25, 800)).toBe('5 Days')
    expect(estimatedFullLabel(10, 0)).toBe('Unknown')
    expect(estimatedFullLabel(null, 100)).toBe('Unknown')
  })
})
