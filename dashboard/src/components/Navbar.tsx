import { memo } from 'react'
import styles from './Layout.module.css'

interface NavbarProps {
  sidebarOpen: boolean
  onToggleSidebar: () => void
}

export const Navbar = memo(function Navbar({ sidebarOpen, onToggleSidebar }: NavbarProps) {
  return (
    <header className={styles.navbar}>
      <button
        className={styles.menuButton}
        type="button"
        aria-expanded={sidebarOpen}
        aria-controls="app-sidebar"
        aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
        onClick={onToggleSidebar}
      >
        <span aria-hidden="true">{sidebarOpen ? '✕' : '☰'}</span>
      </button>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          HM
        </span>
        <span>HomeLab Monitor</span>
      </div>
      <span className={styles.environment}>Read-only dashboard</span>
    </header>
  )
})
