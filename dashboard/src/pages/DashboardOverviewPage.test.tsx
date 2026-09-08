import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/AuthContext'
import type { BackupStatus, DashboardOverview } from '../types/dashboard'
import { DashboardOverviewPage } from './DashboardOverviewPage'

vi.mock('../api/dashboard', () => ({
  getDashboardOverview: vi.fn(),
  getAgents: vi.fn(),
  getActiveAlerts: vi.fn(),
  getBackupStatus: vi.fn(),
}))

import { getActiveAlerts, getAgents, getBackupStatus, getDashboardOverview } from '../api/dashboard'

const overview: DashboardOverview = {
  agents: { total: 2, online: 1, offline: 1 },
  reports: { total: 4 },
  groups: { total: 0 },
  group_stats: [],
}

const backup: BackupStatus = {
  read_only: true,
  status: 'running',
  backup_health: 'healthy',
  job_name: 'Daily replication to TS-253 Pro',
  job_type: 'replication',
  progress_percent: 43,
  last_backup: '2026-09-08T02:00:00+00:00',
  next_backup: '2026-09-09T02:00:00+00:00',
  duration_seconds: 1080,
  backup_size_bytes: 2_001_111_162_552,
  last_error: '',
  last_success: '2026-09-08T02:00:00+00:00',
  updated_at: '2026-09-08T02:18:00Z',
  destination: { hostname: 'qnap-backup-01', ip: '192.168.1.253', model: 'TS-253 Pro' },
  history: [
    { period: 'yesterday', label: 'Yesterday', status: 'success' },
    { period: 'today', label: 'Today', status: 'running' },
    { period: 'last_week', label: 'Last Week', status: 'failed' },
  ],
}

function renderPage() {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'user-admin',
          username: 'admin',
          full_name: 'Administrator',
          role: 'admin',
          is_active: true,
        },
        loading: false,
        login: async () => undefined,
        logout: () => undefined,
      }}
    >
      <DashboardOverviewPage />
    </AuthContext.Provider>,
  )
}

describe('Dashboard overview backup cards', () => {
  beforeEach(() => {
    vi.mocked(getDashboardOverview).mockResolvedValue(overview)
    vi.mocked(getAgents).mockResolvedValue([])
    vi.mocked(getActiveAlerts).mockResolvedValue([])
    vi.mocked(getBackupStatus).mockResolvedValue(backup)
  })

  it('keeps existing summary cards and adds backup cards', async () => {
    renderPage()
    expect(await screen.findByLabelText('Total Agents 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Online 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Offline 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Total Reports 4')).toBeInTheDocument()
    expect(screen.getByLabelText('Total Groups 0')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Backup' })).toBeInTheDocument()
    expect(screen.getByLabelText('Backup TS-253 Pro')).toBeInTheDocument()
    expect(screen.getByLabelText('Healthy healthy')).toBeInTheDocument()
    expect(screen.getByLabelText('Running % 43.0%')).toBeInTheDocument()
  })
})
