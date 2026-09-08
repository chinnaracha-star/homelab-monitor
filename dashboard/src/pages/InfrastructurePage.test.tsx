import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/AuthContext'
import type { InfrastructureSummary } from '../types/dashboard'
import { InfrastructurePage } from './InfrastructurePage'

vi.mock('../api/dashboard', () => ({
  getInfrastructure: vi.fn(),
}))

import { getInfrastructure } from '../api/dashboard'

const mockedGet = vi.mocked(getInfrastructure)

const payload: InfrastructureSummary = {
  collected_at: '2026-09-08T01:00:00Z',
  services: [
    {
      service: 'qnap',
      status: 'healthy',
      version: '5.2.1',
      updated_at: '2026-09-08T01:00:00Z',
      summary: { hostname: 'qnap-lab-01', online: true },
    },
    {
      service: 'docker',
      status: 'healthy',
      version: '27.3.1',
      updated_at: '2026-09-08T01:00:00Z',
      summary: { running_containers: 12, stopped_containers: 2 },
    },
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
      <InfrastructurePage />
    </AuthContext.Provider>,
  )
}

describe('Infrastructure page', () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedGet.mockResolvedValue(payload)
  })

  it('renders connector cards with status and summary', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Infrastructure' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'QNAP connector' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Docker connector' })).toBeInTheDocument()
    expect(screen.getByText('qnap-lab-01')).toBeInTheDocument()
    expect(screen.getByText('Version 5.2.1')).toBeInTheDocument()
  })

  it('retries after an API failure', async () => {
    const user = userEvent.setup()
    mockedGet.mockRejectedValueOnce(new Error('offline'))
    mockedGet.mockResolvedValue(payload)
    renderPage()
    expect(await screen.findByText('Infrastructure API failed')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry section' }))
    expect(await screen.findByRole('article', { name: 'QNAP connector' })).toBeInTheDocument()
  })

  it('shows a loading state before data arrives', async () => {
    mockedGet.mockReturnValue(new Promise(() => undefined))
    renderPage()
    expect(await screen.findByLabelText('Loading overview')).toBeInTheDocument()
  })

  it('shows an empty state when no connectors report', async () => {
    mockedGet.mockResolvedValue({ collected_at: '2026-09-08T01:00:00Z', services: [] })
    renderPage()
    expect(
      await screen.findByText('No infrastructure connectors reported a snapshot.'),
    ).toBeInTheDocument()
  })

  it('retries a single connector card', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('article', { name: 'QNAP connector' })
    await user.click(screen.getAllByRole('button', { name: 'Retry' })[0])
    await waitFor(() => expect(mockedGet.mock.calls.length).toBeGreaterThan(1))
  })
})
