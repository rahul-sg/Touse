import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { resetPassword } from '../utils/api'
import styles from './Login.module.css'

interface ResetForm {
  new_password: string
  confirm_password: string
}

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ResetForm>({ defaultValues: { new_password: '', confirm_password: '' } })

  const newPassword = watch('new_password')

  async function onSubmit(data: ResetForm) {
    setServerError('')
    setIsLoading(true)
    try {
      await resetPassword(token, data.new_password)
      setSubmitted(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not reset password. The link may be expired.'
      setServerError(typeof msg === 'string' ? msg : 'Reset failed.')
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <h1 className={styles.title}>Reset password</h1>
          <div className={styles.errorBanner}>
            This reset link is missing its token. Please request a new one.
          </div>
          <p className={styles.altLink}>
            <Link to="/forgot-password">Get a new reset link →</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Choose a new password</h1>

        {submitted ? (
          <div className={styles.errorBanner} style={{ background: '#e7f4ee', color: '#1C3A2F' }}>
            Password updated. Redirecting to sign in…
          </div>
        ) : (
          <>
            {serverError && <div className={styles.errorBanner}>{serverError}</div>}
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <div className={styles.field}>
                <label htmlFor="new_password">New password</label>
                <input
                  id="new_password"
                  type="password"
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  {...register('new_password', {
                    required: 'Required',
                    minLength: { value: 8, message: 'At least 8 characters' },
                  })}
                />
                {errors.new_password && <p className={styles.error}>{errors.new_password.message}</p>}
              </div>

              <div className={styles.field}>
                <label htmlFor="confirm_password">Confirm new password</label>
                <input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  {...register('confirm_password', {
                    required: 'Required',
                    validate: (v) => v === newPassword || 'Passwords do not match',
                  })}
                />
                {errors.confirm_password && <p className={styles.error}>{errors.confirm_password.message}</p>}
              </div>

              <button className={styles.submitBtn} type="submit" disabled={isLoading}>
                {isLoading ? 'Updating…' : 'Update password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
