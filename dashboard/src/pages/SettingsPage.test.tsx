import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/AuthContext'
import { PwaProvider } from '../pwa/PwaProvider'
import type { NotificationSettings } from '../types/dashboard'
import { SettingsPage } from './SettingsPage'

vi.mock('../api/dashboard', () => ({
  getNotificationSettings: vi.fn(),
  updateNotificationSettings: vi.fn(),
  sendTestNotification: vi.fn(),
  sendTelegramTestReport: vi.fn(),
  getRemoteAccess: vi.fn(),
}))

import {
  getNotificationSettings,
  getRemoteAccess,
  sendTelegramTestReport,
  sendTestNotification,
  updateNotificationSettings,
} from '../api/dashboard'

const mockedGet = vi.mocked(getNotificationSettings)
const mockedUpdate = vi.mocked(updateNotificationSettings)
const mockedTest = vi.mocked(sendTestNotification)
const mockedReport = vi.mocked(sendTelegramTestReport)
const mockedRemote = vi.mocked(getRemoteAccess)

const remote = {
  enabled: true,
  provider: 'tailscale',
  hostname: 'homelab-monitor.tailnet.ts.net',
  tailnet_ip: '100.64.0.12',
  https: true,
  serve_enabled: true,
  funnel_enabled: false,
  public: false,
  status: 'connected' as const,
}

function renderSettings(role: 'admin' | 'operator' | 'viewer' = 'admin') {
  return render(
    <PwaProvider>
      <AuthContext.Provider
        value={{
          user: {
            id: `user-${role}`,
            username: role,
            full_name: role,
            role,
            is_active: true,
          },
          loading: false,
          login: async () => undefined,
          logout: () => undefined,
        }}
      >
        <SettingsPage />
      </AuthContext.Provider>
    </PwaProvider>,
  )
}

const settings: NotificationSettings = {
  telegram: {
    enabled: false,
    configured: false,
    api_base_url: 'https://api.telegram.org',
    chat_id: '',
    bot_token_set: false,
    last_test: null,
  },
  discord: { enabled: false, configured: false, webhook_url_set: false },
  slack: { enabled: false, configured: false, webhook_url_set: false },
  email: {
    enabled: false,
    configured: false,
    host: '',
    port: 587,
    username: '',
    from_address: '',
    to_address: '',
    use_tls: true,
    password_set: false,
  },
  reports: {
    hourly_enabled: false,
    daily_enabled: false,
    weekly_enabled: false,
    hour_interval: 1,
    daily_time: '08:00',
    weekly_day: 'sunday',
    weekly_time: '08:00',
    timezone: 'Asia/Bangkok',
    hourly: { enabled: false, last_sent: null, next_scheduled: '2026-09-08T10:00:00+07:00', status: 'disabled' },
    daily: { enabled: false, last_sent: null, next_scheduled: '2026-09-09T08:00:00+07:00', status: 'disabled' },
    weekly: { enabled: false, last_sent: null, next_scheduled: '2026-09-13T08:00:00+07:00', status: 'disabled' },
  },
}

describe('Settings page', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedUpdate.mockReset()
    mockedTest.mockReset()
    mockedReport.mockReset()
    mockedRemote.mockReset()
    mockedRemote.mockResolvedValue(remote)
    mockedGet.mockResolvedValue(settings)
    mockedUpdate.mockResolvedValue({
      ...settings,
      discord: { enabled: true, configured: true, webhook_url_set: true },
    })
  })

  it('saves notification channel settings', async () => {
    const user = userEvent.setup()
    renderSettings()
    expect(await screen.findByRole('heading', { name: 'Telegram' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Discord' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Slack' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Email' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Scheduled Reports' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Telegram Test' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Deployment' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Application' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Remote Access' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy URL' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Test Report' })).toBeInTheDocument()
    expect(screen.getByLabelText('Scheduled report cards').className).toMatch(/statGrid/)
    expect(screen.getByLabelText('Hourly Report Disabled')).toBeInTheDocument()
    expect(screen.getAllByText(/Last Sent:/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Next Scheduled:/).length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Enable Hourly Report')).toBeInTheDocument()
    expect(screen.getByText('Not configured')).toBeInTheDocument()
    expect(screen.getByText(/Last test:/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Test Message' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Discord test' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Slack test' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send email test' })).toBeInTheDocument()
    await user.click(screen.getByLabelText('Enable Discord'))
    await user.type(screen.getByLabelText('Discord webhook URL'), 'https://discord.example/api')
    await user.click(screen.getByRole('button', { name: 'Save notification settings' }))
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled())
  })

  it('sends a Telegram test message and refreshes last test', async () => {
    const user = userEvent.setup()
    mockedTest.mockResolvedValue({
      total: 1,
      notifications: [{ id: 'n1', channel: 'telegram', status: 'sent' }],
    })
    mockedGet
      .mockResolvedValueOnce(settings)
      .mockResolvedValueOnce({
        ...settings,
        telegram: {
          ...settings.telegram,
          configured: true,
          last_test: '2026-09-08T02:00:00+00:00',
        },
      })
    renderSettings()
    expect(await screen.findByText('Last test: Never')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Test Message' }))
    await waitFor(() => expect(mockedTest).toHaveBeenCalledWith('telegram'))
    expect(await screen.findByText('Telegram test message sent.')).toBeInTheDocument()
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })

  it('shows an error state when settings fail to load', async () => {
    mockedGet.mockRejectedValue(new Error('offline'))
    render(
      <PwaProvider>
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
          <SettingsPage />
        </AuthContext.Provider>
      </PwaProvider>,
    )
    expect(await screen.findByText('offline')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry section' })).toBeInTheDocument()
  })

  it('hides the test report button for operators', async () => {
    renderSettings('operator')
    expect(await screen.findByRole('heading', { name: 'Scheduled Reports' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Send Test Report' })).not.toBeInTheDocument()
  })

  it('sends a Telegram test report with loading, success, and error toasts', async () => {
    const user = userEvent.setup()
    let finish: ((value: { status: string; notification_id: string; sent_at: string; provider: string }) => void) | undefined
    mockedReport.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    renderSettings()
    const button = await screen.findByRole('button', { name: 'Send Test Report' })
    expect(screen.getByRole('heading', { name: 'Telegram Test' }).closest('section')?.className).toMatch(
      /reportsSection/,
    )
    await user.click(button)
    expect(await screen.findByText('Sending...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Test Report' })).toBeDisabled()
    finish?.({
      status: 'sent',
      notification_id: 'n-test',
      sent_at: '2026-09-08T09:42:18Z',
      provider: 'telegram',
    })
    expect(await screen.findByText('Telegram Test Report Sent')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Test Report' })).toBeEnabled()
    mockedReport.mockRejectedValueOnce(new Error('offline'))
    await user.click(screen.getByRole('button', { name: 'Send Test Report' }))
    expect(await screen.findByText('Unable to deliver Telegram report.')).toBeInTheDocument()
  })

  it('copies and opens the remote dashboard URL', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    const open = vi.fn()
    window.open = open
    renderSettings()
    await user.click(await screen.findByRole('button', { name: 'Copy URL' }))
    expect(writeText).toHaveBeenCalledWith('https://homelab-monitor.tailnet.ts.net')
    expect(await screen.findByText('Remote dashboard URL copied.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open Dashboard' }))
    expect(open).toHaveBeenCalledWith(
      'https://homelab-monitor.tailnet.ts.net',
      '_blank',
      'noopener,noreferrer',
    )
  })
})
