import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuth } from '../context/AuthContext'
import { getMe, updateAccount, changePassword, deleteAccount } from '../utils/api'
import styles from './Profile.module.css'

interface AccountForm {
  first_name: string
  last_name: string
  email: string
}

interface PasswordForm {
  current_password: string
  new_password: string
  confirm_password: string
}

type Msg = { ok: boolean; text: string } | null

function extractError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

export default function Profile() {
  const { user, isLoggedIn, updateUser, logout } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [accountMsg, setAccountMsg] = useState<Msg>(null)
  const [passwordMsg, setPasswordMsg] = useState<Msg>(null)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleteMsg, setDeleteMsg] = useState<Msg>(null)
  const [deleting, setDeleting] = useState(false)

  const account = useForm<AccountForm>({
    defaultValues: { first_name: '', last_name: '', email: '' },
  })
  const password = useForm<PasswordForm>({
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  })

  useEffect(() => {
    if (!isLoggedIn || !user) {
      navigate('/login')
      return
    }
    getMe(user.user_id)
      .then(me => {
        account.reset({ first_name: me.first_name, last_name: me.last_name, email: me.email })
        setUsername(me.username)
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, user, navigate])

  async function onSaveAccount(data: AccountForm) {
    if (!user) return
    setAccountMsg(null)
    try {
      const updated = await updateAccount(user.user_id, data)
      updateUser({ first_name: updated.first_name })
      setAccountMsg({ ok: true, text: 'Account details saved.' })
    } catch (err) {
      setAccountMsg({ ok: false, text: extractError(err, 'Could not update your account.') })
    }
  }

  async function onChangePassword(data: PasswordForm) {
    if (!user) return
    setPasswordMsg(null)
    if (data.new_password !== data.confirm_password) {
      setPasswordMsg({ ok: false, text: 'New passwords do not match.' })
      return
    }
    try {
      await changePassword(user.user_id, data.current_password, data.new_password)
      password.reset({ current_password: '', new_password: '', confirm_password: '' })
      setPasswordMsg({ ok: true, text: 'Password changed.' })
    } catch (err) {
      setPasswordMsg({ ok: false, text: extractError(err, 'Could not change your password.') })
    }
  }

  async function onDeleteAccount() {
    if (!user) return
    setDeleteMsg(null)
    setDeleting(true)
    try {
      await deleteAccount(user.user_id)
      logout()
      navigate('/')
    } catch (err) {
      setDeleteMsg({ ok: false, text: extractError(err, 'Could not delete your account.') })
      setDeleting(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <h1 className={styles.title}>Your profile</h1>
        <p className={styles.subtitle}>Manage your account details and password.</p>

        {/* ── Account details ── */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Account details</h2>
          <form onSubmit={account.handleSubmit(onSaveAccount)} noValidate>
            <div className={styles.row}>
              <div className={styles.field}>
                <label>First name</label>
                <input autoComplete="given-name" {...account.register('first_name', { required: true })} />
              </div>
              <div className={styles.field}>
                <label>Last name</label>
                <input autoComplete="family-name" {...account.register('last_name', { required: true })} />
              </div>
            </div>
            <div className={styles.field}>
              <label>Email</label>
              <input
                type="email"
                autoComplete="email"
                autoCapitalize="none"
                spellCheck={false}
                {...account.register('email', { required: true })}
              />
            </div>
            <div className={styles.field}>
              <label>Username</label>
              <input value={username} disabled className={styles.disabledInput} />
              <p className={styles.hint}>Your username can't be changed.</p>
            </div>
            {accountMsg && (
              <p className={accountMsg.ok ? styles.success : styles.error}>{accountMsg.text}</p>
            )}
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={account.formState.isSubmitting}
            >
              {account.formState.isSubmitting ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </div>

        {/* ── Change password ── */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Change password</h2>
          <form onSubmit={password.handleSubmit(onChangePassword)} noValidate>
            <div className={styles.field}>
              <label>Current password</label>
              <input
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                {...password.register('current_password', { required: true })}
              />
            </div>
            <div className={styles.field}>
              <label>New password</label>
              <input
                type="password"
                autoComplete="new-password"
                placeholder="At least 8 characters"
                {...password.register('new_password', { required: true, minLength: 8 })}
              />
            </div>
            <div className={styles.field}>
              <label>Confirm new password</label>
              <input
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                {...password.register('confirm_password', { required: true })}
              />
            </div>
            {passwordMsg && (
              <p className={passwordMsg.ok ? styles.success : styles.error}>{passwordMsg.text}</p>
            )}
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={password.formState.isSubmitting}
            >
              {password.formState.isSubmitting ? 'Saving…' : 'Change password'}
            </button>
          </form>
        </div>

        {/* ── Danger zone ── */}
        <div className={styles.card} style={{ borderColor: '#d4a4a4' }}>
          <h2 className={styles.cardTitle} style={{ color: '#a33' }}>Delete account</h2>
          <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.75rem' }}>
            This permanently removes your account and all your saved scenarios.
            This cannot be undone. Type <strong>DELETE</strong> below to confirm.
          </p>
          <div className={styles.field}>
            <input
              type="text"
              placeholder="Type DELETE to confirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              autoCapitalize="characters"
              spellCheck={false}
            />
          </div>
          {deleteMsg && (
            <p className={deleteMsg.ok ? styles.success : styles.error}>{deleteMsg.text}</p>
          )}
          <button
            type="button"
            className={styles.submitBtn}
            disabled={deleteConfirm !== 'DELETE' || deleting}
            onClick={onDeleteAccount}
            style={{ background: deleteConfirm === 'DELETE' ? '#a33' : undefined }}
          >
            {deleting ? 'Deleting…' : 'Permanently delete my account'}
          </button>
        </div>
      </div>
    </div>
  )
}
