import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { forgotPassword } from '../utils/api'
import styles from './Login.module.css'

interface ForgotForm {
  email: string
}

export default function ForgotPassword() {
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({ defaultValues: { email: '' } })

  async function onSubmit(data: ForgotForm) {
    setServerError('')
    setIsLoading(true)
    try {
      await forgotPassword(data.email.trim())
      setSubmitted(true)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Something went wrong. Please try again.'
      setServerError(typeof msg === 'string' ? msg : 'Request failed.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Forgot password</h1>
        <p className={styles.subtitle}>
          We'll email you a link to reset it.
        </p>

        {submitted ? (
          <div className={styles.errorBanner} style={{ background: '#e7f4ee', color: '#1C3A2F' }}>
            If an account exists for that email, a reset link is on its way.
            Check your inbox (and spam folder).
          </div>
        ) : (
          <>
            {serverError && <div className={styles.errorBanner}>{serverError}</div>}
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <div className={styles.field}>
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  type="email"
                  placeholder="jane@example.com"
                  autoCapitalize="none"
                  autoComplete="email"
                  spellCheck={false}
                  {...register('email', { required: 'Required' })}
                />
                {errors.email && <p className={styles.error}>{errors.email.message}</p>}
              </div>
              <button className={styles.submitBtn} type="submit" disabled={isLoading}>
                {isLoading ? 'Sending…' : 'Send reset link'}
              </button>
            </form>
          </>
        )}

        <p className={styles.altLink}>
          <Link to="/login">← Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}
