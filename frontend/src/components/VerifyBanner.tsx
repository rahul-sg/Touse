import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { resendVerification } from '../utils/api'
import styles from './VerifyBanner.module.css'

/** App-wide banner shown to logged-in users who haven't verified their email. */
export default function VerifyBanner() {
  const { user, isLoggedIn } = useAuth()
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)

  if (!isLoggedIn || !user || user.email_verified) return null

  async function handleResend() {
    if (!user) return
    setSending(true)
    try {
      await resendVerification(user.user_id)
      setSent(true)
    } catch {
      /* ignore — user can try again */
    } finally {
      setSending(false)
    }
  }

  return (
    <div className={styles.banner}>
      <span className={styles.text}>
        Please verify your email address to secure your account.
      </span>
      {sent ? (
        <span className={styles.sent}>Verification email sent ✓</span>
      ) : (
        <button className={styles.resendBtn} onClick={handleResend} disabled={sending}>
          {sending ? 'Sending…' : 'Resend email'}
        </button>
      )}
    </div>
  )
}
