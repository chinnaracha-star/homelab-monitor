import { isNotFound } from '../utils/errors'
import { apiClient } from './client'
import type {
  ActiveAlert,
  AgentDetail,
  AgentHistory,
  AgentSummary,
  DashboardOverview,
  GroupDetail,
  GroupSummary,
  GroupSummaryList,
  LatestMetricReport,
  NotificationDelivery,
  NotificationList,
  NotificationSettings,
  AlertRule,
  AlertRulePayload,
  InfrastructureSnapshot,
  InfrastructureSummary,
  PhotoServicesSummary,
  BackupStatus,
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

export async function getAgentHistory(
  agentId: string,
  params: { from: string; to: string; interval: AgentHistory['interval'] },
): Promise<AgentHistory> {
  const response = await apiClient.get<AgentHistory>(
    `/history/agents/${encodeURIComponent(agentId)}`,
    { params },
  )
  return response.data
}

export async function getGroups(): Promise<GroupSummary[]> {
  const response = await apiClient.get<GroupSummary[]>('/groups')
  return response.data
}

export async function getGroupsSummary(): Promise<GroupSummaryList> {
  const response = await apiClient.get<GroupSummaryList>('/groups/summary')
  return response.data
}

export async function getGroup(groupId: string): Promise<GroupDetail> {
  const response = await apiClient.get<GroupDetail>(`/groups/${encodeURIComponent(groupId)}`)
  return response.data
}

export async function createGroup(payload: { name: string; description: string }): Promise<GroupDetail> {
  const response = await apiClient.post<GroupDetail>('/groups', payload)
  return response.data
}

export async function updateGroup(
  groupId: string,
  payload: { name: string; description: string },
): Promise<GroupDetail> {
  const response = await apiClient.put<GroupDetail>(
    `/groups/${encodeURIComponent(groupId)}`,
    payload,
  )
  return response.data
}

export async function deleteGroup(groupId: string): Promise<void> {
  await apiClient.delete(`/groups/${encodeURIComponent(groupId)}`)
}

export async function assignAgentsToGroup(groupId: string, agentIds: string[]): Promise<GroupDetail> {
  const response = await apiClient.post<GroupDetail>(
    `/groups/${encodeURIComponent(groupId)}/agents`,
    { agent_ids: agentIds },
  )
  return response.data
}

export async function removeAgentFromGroup(groupId: string, agentId: string): Promise<GroupDetail> {
  const response = await apiClient.delete<GroupDetail>(
    `/groups/${encodeURIComponent(groupId)}/agents/${encodeURIComponent(agentId)}`,
  )
  return response.data
}

export async function getNotifications(): Promise<NotificationList> {
  const response = await apiClient.get<NotificationList>('/notifications')
  return response.data
}

export async function getNotification(notificationId: string): Promise<NotificationDelivery> {
  const response = await apiClient.get<NotificationDelivery>(
    `/notifications/${encodeURIComponent(notificationId)}`,
  )
  return response.data
}

export async function sendTestNotification(
  channel?: NotificationDelivery['channel'],
): Promise<NotificationList> {
  const response = await apiClient.post<NotificationList>(
    '/notifications/test',
    channel ? { channel } : {},
  )
  return response.data
}

export async function retryNotification(notificationId: string): Promise<NotificationDelivery> {
  const response = await apiClient.post<NotificationDelivery>(
    `/notifications/${encodeURIComponent(notificationId)}/retry`,
  )
  return response.data
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const response = await apiClient.get<NotificationSettings>('/settings/notifications')
  return response.data
}

export async function updateNotificationSettings(
  payload: Record<string, Record<string, unknown>>,
): Promise<NotificationSettings> {
  const response = await apiClient.put<NotificationSettings>('/settings/notifications', payload)
  return response.data
}

export async function getAlertRules(): Promise<AlertRule[]> {
  const response = await apiClient.get<AlertRule[]>('/alert-rules')
  return response.data
}

export async function createAlertRule(payload: AlertRulePayload): Promise<AlertRule> {
  const response = await apiClient.post<AlertRule>('/alert-rules', payload)
  return response.data
}

export async function updateAlertRule(ruleId: string, payload: AlertRulePayload): Promise<AlertRule> {
  const response = await apiClient.put<AlertRule>(`/alert-rules/${encodeURIComponent(ruleId)}`, payload)
  return response.data
}

export async function setAlertRuleEnabled(ruleId: string, enabled: boolean): Promise<AlertRule> {
  const response = await apiClient.patch<AlertRule>(
    `/alert-rules/${encodeURIComponent(ruleId)}/enable`,
    { enabled },
  )
  return response.data
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  await apiClient.delete(`/alert-rules/${encodeURIComponent(ruleId)}`)
}

export async function getInfrastructure(): Promise<InfrastructureSummary> {
  const response = await apiClient.get<InfrastructureSummary>('/infrastructure')
  return response.data
}

export async function getInfrastructureService(service: string): Promise<InfrastructureSnapshot> {
  const response = await apiClient.get<InfrastructureSnapshot>(
    `/infrastructure/${encodeURIComponent(service)}`,
  )
  return response.data
}

export async function getPhotoServices(): Promise<PhotoServicesSummary> {
  const response = await apiClient.get<PhotoServicesSummary>('/photo-services')
  return response.data
}

export async function getBackupStatus(): Promise<BackupStatus> {
  const response = await apiClient.get<BackupStatus>('/backup')
  return response.data
}
