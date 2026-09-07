import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

if (!apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is required')
}

export const apiClient = axios.create({
  baseURL: apiBaseUrl.replace(/\/+$/, ''),
  headers: {
    Accept: 'application/json',
  },
  timeout: 10_000,
})
