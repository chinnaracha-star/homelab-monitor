import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/AuthContext'
import { PwaContext, type PwaContextValue } from '../pwa/PwaProvider'
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
    vi.mocked(getAgents).mockResolvedValue([
      {
        id: 'agent-online',
        name: 'mini-pc',
        hostname: 'mini-pc.local',
        version: '0.1.0',
        status: 'online',
        last_seen_at: '2026-09-08T08:35:00Z',
      },
    ])
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
    expect(screen.getByLabelText('Status Online')).toBeInTheDocument()
  })

  it('shows the PWA install button and offline shell', async () => {
    const install = vi.fn()
    const pwa: PwaContextValue = {
      installed: false,
      canInstall: true,
      serviceWorker: 'registered',
      cacheReady: true,
      version: '0.1.0',
      updateAvailable: false,
      offline: true,
      install,
      checkForUpdate: vi.fn(),
      applyUpdate: vi.fn(),
      dismissUpdate: vi.fn(),
      clearCache: vi.fn(),
    }
    render(
      <PwaContext.Provider value={pwa}>
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
        </AuthContext.Provider>
      </PwaContext.Provider>,
    )
    expect(await screen.findByLabelText('Total Agents 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Install HomeLab Monitor' })).toBeInTheDocument()
    expect(screen.getByLabelText('Offline status')).toBeInTheDocument()
    expect(screen.getByText('Cached Data')).toBeInTheDocument()
    expect(screen.getByLabelText('Monitoring summary').className).toMatch(/statGrid/)
  })
})
