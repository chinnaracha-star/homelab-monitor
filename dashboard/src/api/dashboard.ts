import { isNotFound } from '../utils/errors'
import { apiClient } from './client'
import type {
  ActiveAlert,
  AgentDetail,
  AgentSummary,
  DashboardOverview,
  LatestMetricReport,
} from '../types/dashboard'

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const response = await apiClient.get<DashboardOverview>('/dashboard/overview')
  return response.data
}

export async function getAgents(): Promise<AgentSummary[]> {
  const response = await apiClient.get<AgentSummary[]>('/agents')
  return response.data
}

export async function getAgent(agentId: string): Promise<AgentDetail> {
  const response = await apiClient.get<AgentDetail>(`/agents/${encodeURIComponent(agentId)}`)
  return response.data
}

export async function getLatestAgentReport(agentId: string): Promise<LatestMetricReport> {
  const response = await apiClient.get<LatestMetricReport>(
    `/agents/${encodeURIComponent(agentId)}/latest-report`,
  )
  return response.data
}

export async function getActiveAlerts(): Promise<ActiveAlert[]> {
  try {
    const response = await apiClient.get<ActiveAlert[]>('/alerts/active')
    return response.data
  } catch (error) {
    if (isNotFound(error)) {
      return []
    }
    throw error
  }
}
