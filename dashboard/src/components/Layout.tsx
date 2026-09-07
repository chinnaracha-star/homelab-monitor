import { useCallback, useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { AlertBanner } from './AlertBanner'
import styles from './Layout.module.css'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

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
      <Navbar
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />
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
          <AlertBanner />
          <Outlet />
        </main>
      </section>
    </section>
  )
}
