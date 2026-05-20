import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { register as registerUser } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import styles from './Onboarding.module.css'

interface AccountData {
  first_name: string
  last_name: string
  email: string
  username: string
  password: string
  confirm_password: string
  target_zip: string
}

function Step1({ onSuccess }: { onSuccess: () => void }) {
  const { login } = useAuth()
  const [serverError, setServerError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AccountData>({
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      username: '',
      password: '',
      confirm_password: '',
      target_zip: '',
    },
  })

  const password = watch('password')

  async function onSubmit(data: AccountData) {
    setServerError('')
    setIsLoading(true)
    try {
      const result = await registerUser({
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        username: data.username,
        password: data.password,
        target_zip: data.target_zip || undefined,
      })
      login({
        user_id: result.user_id,
        username: result.username,
        first_name: result.first_name,
        access_token: result.access_token,
        target_zip: result.target_zip ?? null,
      })
      onSuccess()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Registration failed. Please try again.'
      setServerError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.card}>
      <h1 className={styles.cardTitle}>Create your account</h1>
      <p className={styles.cardSubtitle}>
        Join Touse free. Build scenarios, compare what you can afford, and track homes in your budget.
      </p>

      {serverError && <div className={styles.errorBanner}>{serverError}</div>}

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className={styles.formRow}>
          <div className={styles.field}>
            <label htmlFor="first_name">First name</label>
            <input
              id="first_name"
              type="text"
              placeholder="Jane"
              {...register('first_name', { required: 'Required' })}
            />
            {errors.first_name && <p className={styles.error}>{errors.first_name.message}</p>}
          </div>
          <div className={styles.field}>
            <label htmlFor="last_name">Last name</label>
            <input
              id="last_name"
              type="text"
              placeholder="Smith"
              {...register('last_name', { required: 'Required' })}
            />
            {errors.last_name && <p className={styles.error}>{errors.last_name.message}</p>}
          </div>
        </div>

        <div className={styles.field}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="jane@example.com"
            {...register('email', {
              required: 'Required',
              pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' },
            })}
          />
          {errors.email && <p className={styles.error}>{errors.email.message}</p>}
        </div>

        <div className={styles.field}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            placeholder="janesmith"
            {...register('username', {
              required: 'Required',
              minLength: { value: 3, message: 'At least 3 characters' },
              pattern: { value: /^[a-zA-Z0-9_]+$/, message: 'Letters, numbers, and underscores only' },
            })}
          />
          {errors.username && <p className={styles.error}>{errors.username.message}</p>}
        </div>

        <div className={styles.field}>
          <label htmlFor="target_zip">Where are you looking to buy? <span className={styles.optionalLabel}>(optional)</span></label>
          <input
            id="target_zip"
            type="text"
            placeholder="78701 or Austin, TX"
            {...register('target_zip')}
          />
          <p className={styles.fieldHint}>We'll use this to personalise your map and market forecast.</p>
        </div>

        <div className={styles.field}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            {...register('password', {
              required: 'Required',
              minLength: { value: 8, message: 'At least 8 characters' },
            })}
          />
          {errors.password && <p className={styles.error}>{errors.password.message}</p>}
        </div>

        <div className={styles.field}>
          <label htmlFor="confirm_password">Confirm password</label>
          <input
            id="confirm_password"
            type="password"
            placeholder="••••••••"
            {...register('confirm_password', {
              required: 'Required',
              validate: (val) => val === password || 'Passwords do not match',
            })}
          />
          {errors.confirm_password && (
            <p className={styles.error}>{errors.confirm_password.message}</p>
          )}
        </div>

        <button className={styles.submitBtn} type="submit" disabled={isLoading}>
          {isLoading ? 'Creating account…' : 'Create account →'}
        </button>
      </form>

      <p className={styles.altLink}>
        Already have an account?{' '}
        <Link to="/login">Sign in</Link>
      </p>
    </div>
  )
}

export default function Onboarding() {
  const navigate = useNavigate()
  return (
    <div className={styles.page}>
      <Step1 onSuccess={() => navigate('/dashboard')} />
    </div>
  )
}
