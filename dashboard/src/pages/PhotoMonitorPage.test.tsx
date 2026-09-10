import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PhotoMonitorPage } from './PhotoMonitorPage'

vi.mock('../api/dashboard', () => ({
  getPhotoEvents: vi.fn(),
  getPhotoMonitorStats: vi.fn(),
}))

import { getPhotoEvents, getPhotoMonitorStats } from '../api/dashboard'

describe('Photo Monitor page', () => {
  beforeEach(() => {
    vi.mocked(getPhotoMonitorStats).mockResolvedValue({
      today_count: 128,
      last_photo: 'IMG_20260910_140012.jpg',
      last_folder: 'Pictures-All',
      last_update: '2026-09-10T07:00:12Z',
      watch_folder: '/mnt/picture-all',
      watch_folders: [
        '/mnt/picture-all',
        '/mnt/pictures-ss22',
        '/mnt/pictures-ae',
        '/mnt/picture-mae',
        '/mnt/picture-por',
        '/mnt/pictures-solarboy',
      ],
      watch_folder_labels: [
        'Pictures-All',
        'Pictures-SS22',
        'Pictures-ae',
        'Pictures-แม่',
        'Pictures-พ่อ',
        'Pictures-SolarBoy',
      ],
      indexed_files: 63086,
      status: 'running',
      enabled: true,
    })
    vi.mocked(getPhotoEvents).mockResolvedValue({
      items: [
        {
          id: 1,
          filename: 'IMG_20260910_140012.jpg',
          folder: '/Picture-All',
          size_bytes: 3_686_400,
          created_at: '2026-09-10T07:00:12Z',
          telegram_sent: true,
        },
      ],
    })
  })

  it('shows summary cards and recent photos', async () => {
    render(<PhotoMonitorPage />)
    expect(await screen.findByRole('heading', { name: 'Photo Monitor' })).toBeInTheDocument()
    expect(screen.getByLabelText("Today's Photos 128")).toBeInTheDocument()
    expect(screen.getByLabelText('Last Photo IMG_20260910_140012.jpg')).toBeInTheDocument()
    expect(screen.getByLabelText('Status 🟢 Running')).toBeInTheDocument()
    expect(screen.getByLabelText('Watching 6 folders')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Folders' })).toBeInTheDocument()
    expect(screen.getAllByText('Pictures-All').length).toBeGreaterThan(0)
    expect(screen.getByText('Pictures-SS22')).toBeInTheDocument()
    expect(screen.getByText('Pictures-แม่')).toBeInTheDocument()
    expect(screen.getByLabelText('Last Folder Pictures-All')).toBeInTheDocument()
    expect(screen.getByLabelText(`Indexed Files ${Number(63086).toLocaleString()} files indexed`)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Recent Photos' })).toBeInTheDocument()
    expect(screen.getAllByText('IMG_20260910_140012.jpg').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Sent')).toBeInTheDocument()
  })
})
