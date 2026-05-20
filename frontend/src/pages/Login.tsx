import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { loginUser } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import styles from './Login.module.css'

interface LoginForm {
  email: string
  password: string
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    defaultValues: { email: '', password: '' },
  })

  async function onSubmit(data: LoginForm) {
    setServerError('')
    setIsLoading(true)
    try {
      const result = await loginUser(data.email, data.password)
      login({
        user_id: result.user_id,
        username: result.username,
        first_name: result.first_name,
        access_token: result.access_token,
      })
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Invalid email or password. Please try again.'
      setServerError(typeof msg === 'string' ? msg : 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Sign in</h1>
        <p className={styles.subtitle}>Welcome back to Touse.</p>

        {serverError && <div className={styles.errorBanner}>{serverError}</div>}

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
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
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              {...register('password', { required: 'Required' })}
            />
            {errors.password && <p className={styles.error}>{errors.password.message}</p>}
          </div>

          <button className={styles.submitBtn} type="submit" disabled={isLoading}>
            {isLoading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className={styles.altLink}>
          New to Touse?{' '}
          <Link to="/onboarding">Get started →</Link>
        </p>
      </div>
    </div>
  )
}
