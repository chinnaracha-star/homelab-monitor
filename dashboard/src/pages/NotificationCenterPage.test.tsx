import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NotificationCenterStatistics, NotificationHistory } from '../types/dashboard'
import { NotificationCenterPage } from './NotificationCenterPage'

vi.mock('../api/dashboard', () => ({
  getNotificationHistory: vi.fn(),
  getNotificationCenterStatistics: vi.fn(),
}))

import { getNotificationCenterStatistics, getNotificationHistory } from '../api/dashboard'

const stats: NotificationCenterStatistics = {
  unread: 1,
  today: 1,
  this_week: 1,
  critical: 1,
  total: 1,
}

const history: NotificationHistory = {
  items: [
    {
      id: 'n1',
      title: 'cpu high',
      description: 'CPU recovered',
      severity: 'critical',
      source: 'telegram',
      kind: 'alert',
      agent_id: 'agent-1',
      agent_name: 'home-srv-01',
      read_state: 'unread',
      created_at: '2026-09-08T08:00:00Z',
    },
    {
      id: 'n2',
      title: 'Hourly Report',
      description: 'Sent',
      severity: 'info',
      source: 'telegram',
      kind: 'hourly_report',
      agent_id: null,
      agent_name: null,
      read_state: 'read',
      created_at: '2026-09-08T09:00:00Z',
    },
    {
      id: 'n3',
      title: 'Test Report',
      description: 'Sent',
      severity: 'info',
      source: 'telegram',
      kind: 'test_report',
      agent_id: null,
      agent_name: null,
      read_state: 'read',
      created_at: '2026-09-08T09:05:00Z',
    },
  ],
  groups: [],
}

describe('Notification Center page', () => {
  beforeEach(() => {
    vi.mocked(getNotificationCenterStatistics).mockResolvedValue(stats)
    vi.mocked(getNotificationHistory).mockResolvedValue(history)
  })

  it('renders cards, timeline, and filters', async () => {
    render(<NotificationCenterPage />)
    expect(await screen.findByRole('heading', { name: 'Notification Center' })).toBeInTheDocument()
    expect(screen.getByLabelText('Unread 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Notification timeline')).toBeInTheDocument()
    expect(screen.getByLabelText('Notification filters')).toBeInTheDocument()
    expect(screen.getByText('Hourly Report')).toBeInTheDocument()
    expect(screen.getByText('Test Report')).toBeInTheDocument()
  })

  it('shows empty and retry', async () => {
    vi.mocked(getNotificationHistory).mockResolvedValue({ items: [], groups: [] })
    render(<NotificationCenterPage />)
    expect(await screen.findByText('No notifications yet.')).toBeInTheDocument()
    expect(screen.getByLabelText('Notification filters').className).toMatch(/filterBar/)
  })

  it('retries after an error', async () => {
    vi.mocked(getNotificationHistory).mockRejectedValue(new Error('failed'))
    vi.mocked(getNotificationCenterStatistics).mockRejectedValue(new Error('failed'))
    render(<NotificationCenterPage />)
    expect(await screen.findByText('Notification center failed')).toBeInTheDocument()
    vi.mocked(getNotificationHistory).mockResolvedValue(history)
    vi.mocked(getNotificationCenterStatistics).mockResolvedValue(stats)
    await userEvent.click(screen.getByRole('button', { name: 'Retry section' }))
    await waitFor(() => {
      expect(screen.getByLabelText('Notification timeline')).toBeInTheDocument()
    })
  })
})
