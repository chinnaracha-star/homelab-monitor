import styles from './Pages.module.css'

export function SettingsPage() {
  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Administration</p>
          <h1 className={styles.title}>Settings</h1>
          <p className={styles.description}>
            System settings can only be changed by administrators.
          </p>
        </div>
      </header>
    </section>
  )
}
