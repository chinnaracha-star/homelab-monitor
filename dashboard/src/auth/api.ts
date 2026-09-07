import { apiClient } from '../api/client'

export interface AuthUser {
  id: string
  username: string
  full_name: string
  role: string
  is_active: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', { username, password })
  return response.data
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await apiClient.get<AuthUser>('/auth/me')
  return response.data
}
