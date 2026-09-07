import { memo } from 'react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../auth/permissions'
import { useCan } from '../auth/useCan'
import styles from './Layout.module.css'

interface SidebarProps {
  open: boolean
  onNavigate: () => void
}

function navClassName({ isActive }: { isActive: boolean }) {
  return `${styles.navLink} ${isActive ? styles.active : ''}`.trim()
}

export const Sidebar = memo(function Sidebar({ open, onNavigate }: SidebarProps) {
  const can = useCan()
  const items = NAV_ITEMS.filter((item) => can(item.permission))

  return (
    <aside
      className={`${styles.sidebar} ${open ? styles.sidebarOpen : ''}`}
      id="app-sidebar"
    >
      <nav className={styles.navigation} aria-label="Primary navigation">
        {items.map((item) => (
          <NavLink
            className={navClassName}
            key={item.to}
            to={item.to}
            onClick={onNavigate}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
})
