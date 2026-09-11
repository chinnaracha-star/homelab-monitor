export const APP_VERSION = '1.0.0-rc1'

export const pwaManifest = {
  name: 'HomeLab Monitor',
  short_name: 'HomeLab',
  description: 'Read-only dashboard for HomeLab Monitor agents and system metrics',
  theme_color: '#111827',
  background_color: '#111827',
  display: 'standalone' as const,
  orientation: 'portrait' as const,
  scope: '/',
  start_url: '/',
  lang: 'en',
  icons: [
    {
      src: '/icons/icon-192.png',
      sizes: '192x192',
      type: 'image/png',
      purpose: 'any',
    },
    {
      src: '/icons/icon-512.png',
      sizes: '512x512',
      type: 'image/png',
      purpose: 'any',
    },
    {
      src: '/icons/icon-maskable-192.png',
      sizes: '192x192',
      type: 'image/png',
      purpose: 'maskable',
    },
    {
      src: '/icons/icon-maskable-512.png',
      sizes: '512x512',
      type: 'image/png',
      purpose: 'maskable',
    },
  ],
}

export function isStandaloneDisplay(media: { matches: boolean } | null, standaloneFlag?: boolean): boolean {
  return Boolean(standaloneFlag) || Boolean(media?.matches)
}

export function serviceWorkerLabel(registered: boolean): 'Registered' | 'Missing' {
  return registered ? 'Registered' : 'Missing'
}

export function cacheStatusLabel(ready: boolean): 'Ready' | 'Empty' {
  return ready ? 'Ready' : 'Empty'
}
