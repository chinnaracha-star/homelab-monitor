import { memo } from 'react'
import { NavLink } from 'react-router-dom'
import styles from './Layout.module.css'

interface SidebarProps {
  open: boolean
  onNavigate: () => void
}

function navClassName({ isActive }: { isActive: boolean }) {
  return `${styles.navLink} ${isActive ? styles.active : ''}`.trim()
}

export const Sidebar = memo(function Sidebar({ open, onNavigate }: SidebarProps) {
  return (
    <aside
      className={`${styles.sidebar} ${open ? styles.sidebarOpen : ''}`}
      id="app-sidebar"
    >
      <nav className={styles.navigation} aria-label="Primary navigation">
        <NavLink className={navClassName} to="/" end onClick={onNavigate}>
          Overview
        </NavLink>
        <NavLink className={navClassName} to="/agents" onClick={onNavigate}>
          Agents
        </NavLink>
        <NavLink className={navClassName} to="/alerts" onClick={onNavigate}>
          Alerts
        </NavLink>
      </nav>
    </aside>
  )
})
