import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  getNotificationSettings,
  sendTestNotification,
  updateNotificationSettings,
} from '../api/dashboard'
import { useCan } from '../auth/useCan'
import { SectionError } from '../components/SectionError'
import { OverviewSkeleton } from '../components/Skeleton'
import { getErrorMessage } from '../utils/errors'
import userStyles from './UsersPage.module.css'
import pageStyles from './Pages.module.css'
import styles from './SettingsPage.module.css'
import type { NotificationSettings } from '../types/dashboard'

const emptySettings: NotificationSettings = {
  telegram: {
    enabled: false,
    configured: false,
    api_base_url: '',
    chat_id: '',
    bot_token_set: false,
    last_test: null,
  },
  discord: { enabled: false, configured: false, webhook_url_set: false },
  slack: { enabled: false, configured: false, webhook_url_set: false },
  email: {
    enabled: false,
    configured: false,
    host: '',
    port: 587,
    username: '',
    from_address: '',
    to_address: '',
    use_tls: true,
    password_set: false,
  },
}

export function SettingsPage() {
  const canSend = useCan()('send_notifications')
  const [settings, setSettings] = useState<NotificationSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [telegramToken, setTelegramToken] = useState('')
  const [discordUrl, setDiscordUrl] = useState('')
  const [slackUrl, setSlackUrl] = useState('')
  const [emailPassword, setEmailPassword] = useState('')

  const loadSettings = useCallback(() => {
    setError(null)
    void getNotificationSettings()
      .then(setSettings)
      .catch((requestError: unknown) => setError(getErrorMessage(requestError)))
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!settings) {
      return
    }
    setError(null)
    try {
      const saved = await updateNotificationSettings({
        telegram: {
          enabled: settings.telegram.enabled,
          api_base_url: settings.telegram.api_base_url,
          chat_id: settings.telegram.chat_id,
          ...(telegramToken ? { bot_token: telegramToken } : {}),
        },
        discord: {
          enabled: settings.discord.enabled,
          ...(discordUrl ? { webhook_url: discordUrl } : {}),
        },
        slack: {
          enabled: settings.slack.enabled,
          ...(slackUrl ? { webhook_url: slackUrl } : {}),
        },
        email: {
          enabled: settings.email.enabled,
          host: settings.email.host,
          port: settings.email.port,
          username: settings.email.username,
          from_address: settings.email.from_address,
          to_address: settings.email.to_address,
          use_tls: settings.email.use_tls,
          ...(emailPassword ? { password: emailPassword } : {}),
        },
      })
      setSettings(saved)
      setTelegramToken('')
      setDiscordUrl('')
      setSlackUrl('')
      setEmailPassword('')
      setToast('Notification settings saved.')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }
  }

  async function handleTest(channel: 'telegram' | 'discord' | 'slack' | 'email') {
    setError(null)
    try {
      await sendTestNotification(channel)
      setToast(channel === 'telegram' ? 'Telegram test message sent.' : `Test sent on ${channel}.`)
      if (channel === 'telegram') {
        const refreshed = await getNotificationSettings()
        setSettings(refreshed)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }
  }

  const current = settings ?? emptySettings

  return (
    <section className={pageStyles.page}>
      <header className={pageStyles.pageHeader}>
        <div>
          <p className={pageStyles.eyebrow}>Administration</p>
          <h1 className={pageStyles.title}>Settings</h1>
          <p className={pageStyles.description}>Configure notification channels. Secrets are never displayed.</p>
        </div>
      </header>
      {toast ? (
        <p className={userStyles.toast} role="status">
          {toast}
        </p>
      ) : null}
      {error ? <SectionError title={error} onRetry={loadSettings} /> : null}
      {!settings && !error ? <OverviewSkeleton /> : null}
      {settings ? (
        <form className={styles.channelGrid} onSubmit={(event) => void handleSave(event)}>
          <article className={styles.channelCard} aria-labelledby="telegram-settings">
            <h2 className={styles.channelTitle} id="telegram-settings">
              Telegram
            </h2>
            <p className={styles.channelHint}>
              {current.telegram.configured ? 'Configured' : 'Not configured'}
            </p>
            <p className={styles.channelHint}>
              Last test:{' '}
              {current.telegram.last_test
                ? new Date(current.telegram.last_test).toLocaleString()
                : 'Never'}
            </p>
            <label className={userStyles.checkbox} htmlFor="telegram-enabled">
              <input
                id="telegram-enabled"
                type="checkbox"
                checked={current.telegram.enabled}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    telegram: { ...current.telegram, enabled: event.target.checked },
                  })
                }
              />
              Enable Telegram
            </label>
            <label className={userStyles.label} htmlFor="telegram-url">
              API base URL
              <input
                className={userStyles.input}
                id="telegram-url"
                value={current.telegram.api_base_url}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    telegram: { ...current.telegram, api_base_url: event.target.value },
                  })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="telegram-chat">
              Chat ID
              <input
                className={userStyles.input}
                id="telegram-chat"
                value={current.telegram.chat_id}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    telegram: { ...current.telegram, chat_id: event.target.value },
                  })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="telegram-token">
              Bot token
              <input
                className={userStyles.input}
                id="telegram-token"
                type="password"
                autoComplete="off"
                value={telegramToken}
                placeholder={current.telegram.bot_token_set ? 'Stored token unchanged' : ''}
                onChange={(event) => setTelegramToken(event.target.value)}
              />
            </label>
            {canSend ? (
              <button className={userStyles.secondaryButton} type="button" onClick={() => void handleTest('telegram')}>
                Test Message
              </button>
            ) : null}
          </article>

          <article className={styles.channelCard} aria-labelledby="discord-settings">
            <h2 className={styles.channelTitle} id="discord-settings">
              Discord
            </h2>
            <label className={userStyles.checkbox} htmlFor="discord-enabled">
              <input
                id="discord-enabled"
                type="checkbox"
                checked={current.discord.enabled}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    discord: { ...current.discord, enabled: event.target.checked },
                  })
                }
              />
              Enable Discord
            </label>
            <label className={userStyles.label} htmlFor="discord-webhook">
              Discord webhook URL
              <input
                className={userStyles.input}
                id="discord-webhook"
                type="password"
                autoComplete="off"
                value={discordUrl}
                placeholder={current.discord.webhook_url_set ? 'Stored webhook unchanged' : 'https://'}
                onChange={(event) => setDiscordUrl(event.target.value)}
              />
            </label>
            {canSend ? (
              <button className={userStyles.secondaryButton} type="button" onClick={() => void handleTest('discord')}>
                Send Discord test
              </button>
            ) : null}
          </article>

          <article className={styles.channelCard} aria-labelledby="slack-settings">
            <h2 className={styles.channelTitle} id="slack-settings">
              Slack
            </h2>
            <label className={userStyles.checkbox} htmlFor="slack-enabled">
              <input
                id="slack-enabled"
                type="checkbox"
                checked={current.slack.enabled}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    slack: { ...current.slack, enabled: event.target.checked },
                  })
                }
              />
              Enable Slack
            </label>
            <label className={userStyles.label} htmlFor="slack-webhook">
              Slack webhook URL
              <input
                className={userStyles.input}
                id="slack-webhook"
                type="password"
                autoComplete="off"
                value={slackUrl}
                placeholder={current.slack.webhook_url_set ? 'Stored webhook unchanged' : 'https://'}
                onChange={(event) => setSlackUrl(event.target.value)}
              />
            </label>
            {canSend ? (
              <button className={userStyles.secondaryButton} type="button" onClick={() => void handleTest('slack')}>
                Send Slack test
              </button>
            ) : null}
          </article>

          <article className={styles.channelCard} aria-labelledby="email-settings">
            <h2 className={styles.channelTitle} id="email-settings">
              Email
            </h2>
            <label className={userStyles.checkbox} htmlFor="email-enabled">
              <input
                id="email-enabled"
                type="checkbox"
                checked={current.email.enabled}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, enabled: event.target.checked },
                  })
                }
              />
              Enable email
            </label>
            <label className={userStyles.label} htmlFor="email-host">
              SMTP host
              <input
                className={userStyles.input}
                id="email-host"
                value={current.email.host}
                onChange={(event) =>
                  setSettings({ ...current, email: { ...current.email, host: event.target.value } })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="email-port">
              Port
              <input
                className={userStyles.input}
                id="email-port"
                type="number"
                value={current.email.port}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, port: Number(event.target.value) },
                  })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="email-username">
              Username
              <input
                className={userStyles.input}
                id="email-username"
                value={current.email.username}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, username: event.target.value },
                  })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="email-password">
              Password
              <input
                className={userStyles.input}
                id="email-password"
                type="password"
                autoComplete="off"
                value={emailPassword}
                placeholder={current.email.password_set ? 'Stored password unchanged' : ''}
                onChange={(event) => setEmailPassword(event.target.value)}
              />
            </label>
            <label className={userStyles.label} htmlFor="email-from">
              From address
              <input
                className={userStyles.input}
                id="email-from"
                value={current.email.from_address}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, from_address: event.target.value },
                  })
                }
              />
            </label>
            <label className={userStyles.label} htmlFor="email-to">
              To address
              <input
                className={userStyles.input}
                id="email-to"
                value={current.email.to_address}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, to_address: event.target.value },
                  })
                }
              />
            </label>
            <label className={userStyles.checkbox} htmlFor="email-tls">
              <input
                id="email-tls"
                type="checkbox"
                checked={current.email.use_tls}
                onChange={(event) =>
                  setSettings({
                    ...current,
                    email: { ...current.email, use_tls: event.target.checked },
                  })
                }
              />
              Use STARTTLS
            </label>
            {canSend ? (
              <button className={userStyles.secondaryButton} type="button" onClick={() => void handleTest('email')}>
                Send email test
              </button>
            ) : null}
          </article>

          <div className={userStyles.dialogActions}>
            <button className={userStyles.primaryButton} type="submit">
              Save notification settings
            </button>
          </div>
        </form>
      ) : null}
    </section>
  )
}
