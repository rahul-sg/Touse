import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { verifyEmail } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import styles from './VerifyEmail.module.css'

type Status = 'verifying' | 'success' | 'error'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const { user, updateUser } = useAuth()
  const [status, setStatus] = useState<Status>('verifying')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setStatus('error')
      return
    }
    let cancelled = false
    verifyEmail(token)
      .then(() => {
        if (cancelled) return
        setStatus('success')
        if (user) updateUser({ email_verified: true })
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {status === 'verifying' && (
          <>
            <div className={styles.spinner} />
            <h1 className={styles.title}>Verifying your email…</h1>
          </>
        )}

        {status === 'success' && (
          <>
            <h1 className={styles.title}>Email verified</h1>
            <p className={styles.text}>
              Your email address is confirmed — your account is all set.
            </p>
            <Link to={user ? '/dashboard' : '/login'} className={styles.btn}>
              {user ? 'Go to dashboard' : 'Sign in'} →
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <h1 className={styles.title}>Verification failed</h1>
            <p className={styles.text}>
              This verification link is invalid or has expired. Sign in and request a fresh
              one from the banner at the top of the page.
            </p>
            <Link to="/login" className={styles.btn}>Sign in →</Link>
          </>
        )}
      </div>
    </div>
  )
}
