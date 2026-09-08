import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/AuthContext'
import type { NotificationSettings } from '../types/dashboard'
import { SettingsPage } from './SettingsPage'

vi.mock('../api/dashboard', () => ({
  getNotificationSettings: vi.fn(),
  updateNotificationSettings: vi.fn(),
  sendTestNotification: vi.fn(),
}))

import {
  getNotificationSettings,
  sendTestNotification,
  updateNotificationSettings,
} from '../api/dashboard'

const mockedGet = vi.mocked(getNotificationSettings)
const mockedUpdate = vi.mocked(updateNotificationSettings)
const mockedTest = vi.mocked(sendTestNotification)

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
}

describe('Settings page', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedUpdate.mockReset()
    mockedTest.mockReset()
    mockedGet.mockResolvedValue(settings)
    mockedUpdate.mockResolvedValue({
      ...settings,
      discord: { enabled: true, configured: true, webhook_url_set: true },
    })
  })

  it('saves notification channel settings', async () => {
    const user = userEvent.setup()
    render(
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
      </AuthContext.Provider>,
    )
    expect(await screen.findByRole('heading', { name: 'Telegram' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Discord' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Slack' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Email' })).toBeInTheDocument()
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
    render(
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
      </AuthContext.Provider>,
    )
    expect(await screen.findByText('Last test: Never')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Test Message' }))
    await waitFor(() => expect(mockedTest).toHaveBeenCalledWith('telegram'))
    expect(await screen.findByText('Telegram test message sent.')).toBeInTheDocument()
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })

  it('shows an error state when settings fail to load', async () => {
    mockedGet.mockRejectedValue(new Error('offline'))
    render(
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
      </AuthContext.Provider>,
    )
    expect(await screen.findByText('offline')).toBeInTheDocument()
  })
})
