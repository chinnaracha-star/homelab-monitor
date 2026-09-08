export type Role = 'admin' | 'operator' | 'viewer'

export type Permission =
  | 'dashboard'
  | 'agents'
  | 'reports'
  | 'alerts'
  | 'acknowledge_alerts'
  | 'groups'
  | 'manage_groups'
  | 'users'
  | 'settings'
  | 'notifications'
  | 'send_notifications'
  | 'alert_rules'
  | 'manage_alert_rules'
  | 'infrastructure'
  | 'photo_services'
  | 'backup'

export interface NavItem {
  to: string
  label: string
  permission: Permission
}

const ROLE_PERMISSIONS: Record<Role, readonly Permission[]> = {
  admin: [
    'dashboard',
    'agents',
    'reports',
    'alerts',
    'acknowledge_alerts',
    'groups',
    'manage_groups',
    'users',
    'settings',
    'notifications',
    'send_notifications',
    'alert_rules',
    'manage_alert_rules',
    'infrastructure',
    'photo_services',
    'backup',
  ],
  operator: [
    'dashboard',
    'agents',
    'reports',
    'alerts',
    'acknowledge_alerts',
    'groups',
    'manage_groups',
    'notifications',
    'send_notifications',
    'alert_rules',
    'infrastructure',
    'photo_services',
    'backup',
  ],
  viewer: [
    'dashboard',
    'agents',
    'reports',
    'alerts',
    'groups',
    'notifications',
    'alert_rules',
    'infrastructure',
    'photo_services',
    'backup',
  ],
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/dashboard', label: 'Overview', permission: 'dashboard' },
  { to: '/agents', label: 'Agents', permission: 'agents' },
  { to: '/groups', label: 'Groups', permission: 'groups' },
  { to: '/infrastructure', label: 'Infrastructure', permission: 'infrastructure' },
  { to: '/photo-services', label: 'Photo Services', permission: 'photo_services' },
  { to: '/backup', label: 'Backup', permission: 'backup' },
  { to: '/alerts', label: 'Alerts', permission: 'alerts' },
  { to: '/alert-rules', label: 'Alert Rules', permission: 'alert_rules' },
  { to: '/notifications', label: 'Notifications', permission: 'notifications' },
  { to: '/users', label: 'Users', permission: 'users' },
  { to: '/settings', label: 'Settings', permission: 'settings' },
]

function isRole(value: string): value is Role {
  return value === 'admin' || value === 'operator' || value === 'viewer'
}

export function can(role: string | null | undefined, permission: Permission): boolean {
  if (!role || !isRole(role)) {
    return false
  }
  return ROLE_PERMISSIONS[role].includes(permission)
}
