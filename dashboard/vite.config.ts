import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxy = env.VITE_API_PROXY_TARGET
    ? {
        '/api': {
          target: env.VITE_API_PROXY_TARGET,
          changeOrigin: true,
        },
      }
    : undefined

  return {
    plugins: [react()],
    server: {
      proxy,
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      env: {
        VITE_API_BASE_URL: '/api/v1',
      },
    },
  }
})
