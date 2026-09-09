import { useCallback, useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { DashboardSocketProvider, useDashboardConnection } from '../hooks/useDashboardSocket'
import { AlertBanner } from './AlertBanner'
import { PwaUpdateBanner } from './PwaUpdateBanner'
import styles from './Layout.module.css'
import { Navbar } from './Navbar'
import { RealtimeDisconnectedBanner } from './RealtimeDisconnectedBanner'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <DashboardSocketProvider>
      <LayoutShell />
    </DashboardSocketProvider>
  )
}

function LayoutShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { status } = useDashboardConnection()
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const toggleSidebar = useCallback(() => setSidebarOpen((open) => !open), [])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeSidebar()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [closeSidebar])

  return (
    <section className={styles.shell}>
      <Navbar sidebarOpen={sidebarOpen} onToggleSidebar={toggleSidebar} />
      <section className={styles.body}>
        {sidebarOpen ? (
          <button
            className={styles.backdrop}
            type="button"
            aria-label="Close navigation"
            onClick={closeSidebar}
          />
        ) : null}
        <Sidebar open={sidebarOpen} onNavigate={closeSidebar} />
        <main className={styles.main} id="main-content">
          <PwaUpdateBanner />
          {status === 'disconnected' ? <RealtimeDisconnectedBanner /> : null}
          <AlertBanner />
          <Outlet />
        </main>
      </section>
    </section>
  )
}
