export interface DashboardOverview {
  agents: {
    total: number
    online: number
    offline: number
  }
  reports: {
    total: number
  }
}

export interface AgentSummary {
  id: string
  name: string
  hostname: string
  version: string
  status: string
  last_seen_at: string | null
}

export interface AgentDetail extends AgentSummary {
  configuration_revision: number
  capabilities: string[]
}

export interface DiskMetrics {
  filesystem: string
  mount_point: string
  filesystem_type: string
  total_bytes: number
  used_bytes: number
  free_bytes: number
  usage_percent: number
}

export interface TemperatureMetrics {
  source: string
  label: string
  current_celsius: number
  high_celsius: number | null
  critical_celsius: number | null
}

export interface SystemMetrics {
  hostname?: string
  os?: {
    distribution: string
    distribution_id: string
    distribution_version: string
    kernel: string
    architecture: string
  }
  cpu?: {
    usage_percent: number
    logical_count: number
    physical_count: number
  }
  memory?: {
    total_bytes: number
    used_bytes: number
    available_bytes: number
    usage_percent: number
  }
  disks?: DiskMetrics[]
  load_average?: {
    '1_minute': number
    '5_minutes': number
    '15_minutes': number
  }
  uptime_seconds?: number
  temperatures?: TemperatureMetrics[]
}

export interface ReportModule {
  module: string
  status: string
  summary: string
  metrics: SystemMetrics | Record<string, unknown>
  diagnostics: Record<string, unknown>
}

export interface LatestMetricReport {
  id: string
  agent_id: string
  report_id: string
  schema_version: string
  observed_at: string
  received_at: string
  payload: {
    modules: ReportModule[]
    [key: string]: unknown
  }
}

export interface HistoryPoint {
  timestamp: string
  cpu_percent: number | null
  memory_percent: number | null
  disk_percent: number | null
  temperature_celsius: number | null
  network_rx_bytes: number | null
  network_tx_bytes: number | null
}

export interface AgentHistory {
  agent_id: string
  interval: '1m' | '5m' | '15m' | '1h'
  from: string
  to: string
  points: HistoryPoint[]
}

export interface ActiveAlert {
  id: string
  agent_id: string
  agent_name: string
  kind: string
  resource: string
  severity: string
  current_value: number | null
  threshold: number | null
  message: string
  opened_at: string
  last_observed_at: string
}
