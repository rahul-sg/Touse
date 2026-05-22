import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { register as registerUser, saveProfile } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import styles from './Onboarding.module.css'

// ── Step 1 — Account creation ─────────────────────────────────────────────────

interface AccountData {
  first_name: string
  last_name: string
  email: string
  username: string
  password: string
  confirm_password: string
  target_zip: string
}

function Step1({ onSuccess }: { onSuccess: (userId: number) => void }) {
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
        email_verified: result.email_verified,
      })
      onSuccess(result.user_id)
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
          <label htmlFor="target_zip">
            Where are you looking to buy?{' '}
            <span className={styles.optionalLabel}>(optional)</span>
          </label>
          <input
            id="target_zip"
            type="text"
            placeholder="78701 or Austin, TX"
            {...register('target_zip')}
          />
          <p className={styles.fieldHint}>We use this to personalise your map and market forecast.</p>
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
          {isLoading ? 'Creating account…' : 'Continue →'}
        </button>
      </form>

      <p className={styles.altLink}>
        Already have an account?{' '}
        <Link to="/login">Sign in</Link>
      </p>
    </div>
  )
}

// ── Step 2 — Financial profile ────────────────────────────────────────────────

interface ProfileData {
  annual_income: number
  monthly_take_home: number
  liquid_savings: number
  brokerage_value: number
  retirement_value: number
  down_payment: number
  credit_score: number
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string
}

const CREDIT_OPTIONS = [
  { label: 'Excellent (760–850)', value: 800 },
  { label: 'Very Good (700–759)', value: 730 },
  { label: 'Good (680–699)', value: 689 },
  { label: 'Fair (660–679)', value: 669 },
  { label: 'Below Average (640–659)', value: 649 },
  { label: 'Poor (620–639)', value: 629 },
  { label: 'Bad (<620)', value: 580 },
]

function Step2({ userId, onSuccess }: { userId: number; onSuccess: () => void }) {
  const { updateTargetZip } = useAuth()
  const [serverError, setServerError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileData>({
    defaultValues: {
      monthly_debt_car: 0,
      monthly_debt_student: 0,
      monthly_debt_credit: 0,
      monthly_debt_other: 0,
      brokerage_value: 0,
      retirement_value: 0,
      credit_score: 730,
    },
  })

  async function onSubmit(data: ProfileData) {
    setServerError('')
    setIsLoading(true)
    try {
      const liquid = Number(data.liquid_savings)
      const brokerage = Number(data.brokerage_value) || 0
      const retirement = Number(data.retirement_value) || 0
      const totalSavings = liquid + brokerage + retirement

      await saveProfile(userId, {
        annual_income: Number(data.annual_income),
        savings: totalSavings,
        down_payment: Number(data.down_payment),
        credit_score: Number(data.credit_score),
        monthly_debt_car: Number(data.monthly_debt_car) || 0,
        monthly_debt_student: Number(data.monthly_debt_student) || 0,
        monthly_debt_credit: Number(data.monthly_debt_credit) || 0,
        monthly_debt_other: Number(data.monthly_debt_other) || 0,
        zip_code: data.zip_code,
        liquid_savings: liquid,
        brokerage_value: brokerage || undefined,
        retirement_value: retirement || undefined,
        monthly_take_home: Number(data.monthly_take_home) || undefined,
      })
      // Keep the AuthContext in sync so MapView can center on the new ZIP
      if (data.zip_code) {
        updateTargetZip(data.zip_code)
      }
      onSuccess()
    } catch {
      setServerError('Could not save your profile. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.card}>
      <h1 className={styles.cardTitle}>Your financial picture</h1>
      <p className={styles.cardSubtitle}>
        This lets us calculate your real home buying budget and readiness score. Everything stays private.
      </p>

      {serverError && <div className={styles.errorBanner}>{serverError}</div>}

      <form onSubmit={handleSubmit(onSubmit)} noValidate>

        {/* Income */}
        <p className={styles.sectionLabel}>Income</p>
        <div className={styles.formRow}>
          <div className={styles.field}>
            <label htmlFor="annual_income">Annual gross income</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                id="annual_income"
                type="number"
                min="0"
                placeholder="95000"
                {...register('annual_income', { required: 'Required', min: 1 })}
              />
            </div>
            {errors.annual_income && <p className={styles.error}>Required</p>}
          </div>
          <div className={styles.field}>
            <label htmlFor="monthly_take_home">
              Monthly take-home{' '}
              <span className={styles.optionalLabel}>(optional)</span>
            </label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                id="monthly_take_home"
                type="number"
                min="0"
                placeholder="6200"
                {...register('monthly_take_home')}
              />
            </div>
            <p className={styles.hint}>After taxes. Helps us show your real cash flow.</p>
          </div>
        </div>

        {/* Assets */}
        <p className={styles.sectionLabel}>Assets</p>
        <div className={styles.field}>
          <label htmlFor="liquid_savings">Liquid savings</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              id="liquid_savings"
              type="number"
              min="0"
              placeholder="40000"
              {...register('liquid_savings', { required: 'Required', min: 0 })}
            />
          </div>
          <p className={styles.hint}>Cash in checking or savings accounts — your most accessible funds.</p>
          {errors.liquid_savings && <p className={styles.error}>Required</p>}
        </div>
        <div className={styles.formRow}>
          <div className={styles.field}>
            <label htmlFor="brokerage_value">
              Brokerage / investments{' '}
              <span className={styles.optionalLabel}>(optional)</span>
            </label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                id="brokerage_value"
                type="number"
                min="0"
                placeholder="0"
                {...register('brokerage_value')}
              />
            </div>
            <p className={styles.hint}>Taxable investment accounts (stocks, ETFs).</p>
          </div>
          <div className={styles.field}>
            <label htmlFor="retirement_value">
              Retirement accounts{' '}
              <span className={styles.optionalLabel}>(optional)</span>
            </label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                id="retirement_value"
                type="number"
                min="0"
                placeholder="0"
                {...register('retirement_value')}
              />
            </div>
            <p className={styles.hint}>401(k), IRA — not counted toward down payment.</p>
          </div>
        </div>

        {/* Down payment */}
        <div className={styles.field}>
          <label htmlFor="down_payment">Down payment available</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              id="down_payment"
              type="number"
              min="0"
              placeholder="60000"
              {...register('down_payment', { required: 'Required', min: 0 })}
            />
          </div>
          <p className={styles.hint}>How much of your savings you plan to put toward the purchase.</p>
          {errors.down_payment && <p className={styles.error}>Required</p>}
        </div>

        {/* Debts */}
        <p className={styles.sectionLabel}>Monthly debts</p>
        <div className={styles.formRow}>
          <div className={styles.field}>
            <label htmlFor="monthly_debt_car">Car payment</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input type="number" min="0" placeholder="0" {...register('monthly_debt_car')} />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="monthly_debt_student">Student loans</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input type="number" min="0" placeholder="0" {...register('monthly_debt_student')} />
            </div>
          </div>
        </div>
        <div className={styles.formRow}>
          <div className={styles.field}>
            <label htmlFor="monthly_debt_credit">Credit card min.</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input type="number" min="0" placeholder="0" {...register('monthly_debt_credit')} />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="monthly_debt_other">Other debt</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input type="number" min="0" placeholder="0" {...register('monthly_debt_other')} />
            </div>
          </div>
        </div>

        {/* Credit & ZIP */}
        <div className={styles.field}>
          <label htmlFor="credit_score">Credit score range</label>
          <select id="credit_score" {...register('credit_score', { required: true })}>
            {CREDIT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label htmlFor="zip_code">Home search ZIP code</label>
          <input
            id="zip_code"
            type="text"
            placeholder="78701"
            maxLength={10}
            {...register('zip_code', { required: 'Required' })}
          />
          {errors.zip_code && <p className={styles.error}>Required</p>}
        </div>

        <button className={styles.submitBtn} type="submit" disabled={isLoading}>
          {isLoading ? 'Saving…' : 'See my budget →'}
        </button>
      </form>
    </div>
  )
}

// ── Onboarding shell ──────────────────────────────────────────────────────────

export default function Onboarding() {
  const navigate = useNavigate()
  const { user, isLoggedIn } = useAuth()
  const [step, setStep] = useState<1 | 2>(isLoggedIn ? 2 : 1)
  const [newUserId, setNewUserId] = useState<number | null>(isLoggedIn ? (user?.user_id ?? null) : null)

  function handleAccountCreated(userId: number) {
    setNewUserId(userId)
    setStep(2)
  }

  function handleProfileSaved() {
    navigate('/dashboard')
  }

  return (
    <div className={styles.page}>
      <div className={styles.stepIndicator}>
        <div className={`${styles.stepDot} ${step >= 1 ? (step > 1 ? styles.done : styles.active) : ''}`}>1</div>
        <div className={styles.stepLine} />
        <div className={`${styles.stepDot} ${step >= 2 ? styles.active : ''}`}>2</div>
      </div>

      {step === 1 && <Step1 onSuccess={handleAccountCreated} />}
      {step === 2 && newUserId != null && (
        <Step2 userId={newUserId} onSuccess={handleProfileSaved} />
      )}
    </div>
  )
}
