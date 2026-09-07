export type Role = 'admin' | 'operator' | 'viewer'

export type Permission =
  | 'dashboard'
  | 'agents'
  | 'reports'
  | 'alerts'
  | 'acknowledge_alerts'
  | 'users'
  | 'settings'

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
    'users',
    'settings',
  ],
  operator: ['dashboard', 'agents', 'reports', 'alerts', 'acknowledge_alerts'],
  viewer: ['dashboard', 'agents', 'reports', 'alerts'],
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/dashboard', label: 'Overview', permission: 'dashboard' },
  { to: '/agents', label: 'Agents', permission: 'agents' },
  { to: '/alerts', label: 'Alerts', permission: 'alerts' },
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
