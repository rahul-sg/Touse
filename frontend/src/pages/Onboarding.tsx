import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { register as registerUser, loginUser, saveProfile } from '../utils/api'
import { api } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import type { AffordabilityResult } from '../types'
import styles from './Onboarding.module.css'

type Step = 1 | 2 | 3

interface AccountData {
  first_name: string
  last_name: string
  email: string
  username: string
  password: string
  confirm_password: string
}

interface FinancialData {
  annual_income: number
  savings: number
  down_payment: number
  credit_score: number
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string
}

const CREDIT_SCORE_OPTIONS = [
  { label: 'Excellent (760–850)', value: 800 },
  { label: 'Very Good (700–759)', value: 730 },
  { label: 'Good (680–699)', value: 689 },
  { label: 'Fair (660–679)', value: 669 },
  { label: 'Below Average (640–659)', value: 649 },
  { label: 'Poor (620–639)', value: 629 },
  { label: 'Bad (<620)', value: 580 },
]

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtRate(r: number) {
  return `${r.toFixed(2)}%`
}

// ── Step indicator ──────────────────────────────────────────────────────────

function StepIndicator({ current }: { current: Step }) {
  return (
    <div className={styles.stepIndicator}>
      {([1, 2, 3] as Step[]).map((s, i) => (
        <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
          {i > 0 && <div className={styles.stepLine} />}
          <div
            className={`${styles.stepDot} ${current === s ? styles.active : ''} ${current > s ? styles.done : ''}`}
          >
            {current > s ? '✓' : s}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Step 1 — Account ────────────────────────────────────────────────────────

function Step1({
  onSuccess,
}: {
  onSuccess: () => void
}) {
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
      })
      login({
        user_id: result.user_id,
        username: result.username,
        first_name: result.first_name,
        access_token: result.access_token,
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
        Join Touse to save your financial profile and track homes in your budget.
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
          {isLoading ? 'Creating account…' : 'Next →'}
        </button>
      </form>

      <p className={styles.altLink}>
        Already have an account?{' '}
        <Link to="/login">Sign in</Link>
      </p>
    </div>
  )
}

// ── Step 2 — Financial profile ──────────────────────────────────────────────

function Step2({
  onSuccess,
}: {
  onSuccess: (result: AffordabilityResult, financialData: FinancialData) => void
}) {
  const { user } = useAuth()
  const [serverError, setServerError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FinancialData>({
    defaultValues: {
      annual_income: undefined,
      savings: undefined,
      down_payment: undefined,
      credit_score: 800,
      monthly_debt_car: 0,
      monthly_debt_student: 0,
      monthly_debt_credit: 0,
      monthly_debt_other: 0,
      zip_code: '',
    },
  })

  async function onSubmit(data: FinancialData) {
    if (!user) return
    setServerError('')
    setIsLoading(true)
    try {
      await saveProfile(user.user_id, {
        annual_income: data.annual_income,
        savings: data.savings,
        down_payment: data.down_payment,
        credit_score: data.credit_score,
        monthly_debt_car: data.monthly_debt_car,
        monthly_debt_student: data.monthly_debt_student,
        monthly_debt_credit: data.monthly_debt_credit,
        monthly_debt_other: data.monthly_debt_other,
        zip_code: data.zip_code,
      })

      const monthlyDebt =
        (data.monthly_debt_car ?? 0) +
        (data.monthly_debt_student ?? 0) +
        (data.monthly_debt_credit ?? 0) +
        (data.monthly_debt_other ?? 0)

      const { data: result } = await api.post<AffordabilityResult>('/api/v1/affordability', {
        annual_income: data.annual_income,
        savings: data.savings,
        monthly_debt: monthlyDebt,
        credit_score: data.credit_score,
        down_payment: data.down_payment,
        zip_code: data.zip_code,
      })

      onSuccess(result, data)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Something went wrong. Please try again.'
      setServerError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.card}>
      <h1 className={styles.cardTitle}>Your financial picture</h1>
      <p className={styles.cardSubtitle}>Help us find homes you can actually afford.</p>

      {serverError && <div className={styles.errorBanner}>{serverError}</div>}

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <p className={styles.sectionLabel}>Income &amp; savings</p>

        <div className={styles.field}>
          <label>Annual income</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              type="number"
              placeholder="85,000"
              {...register('annual_income', {
                required: 'Required',
                min: { value: 1, message: 'Must be positive' },
                valueAsNumber: true,
              })}
            />
          </div>
          {errors.annual_income && <p className={styles.error}>{errors.annual_income.message}</p>}
        </div>

        <div className={styles.field}>
          <label>Total savings</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              type="number"
              placeholder="100,000"
              {...register('savings', {
                required: 'Required',
                min: { value: 0, message: 'Cannot be negative' },
                valueAsNumber: true,
              })}
            />
          </div>
          {errors.savings && <p className={styles.error}>{errors.savings.message}</p>}
        </div>

        <div className={styles.field}>
          <label>Down payment available</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              type="number"
              placeholder="60,000"
              {...register('down_payment', {
                required: 'Required',
                min: { value: 0, message: 'Cannot be negative' },
                valueAsNumber: true,
              })}
            />
          </div>
          <p className={styles.hint}>Usually 3–20% of home price</p>
          {errors.down_payment && <p className={styles.error}>{errors.down_payment.message}</p>}
        </div>

        <p className={styles.sectionLabel}>Debt payments (monthly)</p>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label>Car / auto loan</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                type="number"
                placeholder="0"
                {...register('monthly_debt_car', {
                  min: { value: 0, message: 'Cannot be negative' },
                  valueAsNumber: true,
                })}
              />
            </div>
          </div>
          <div className={styles.field}>
            <label>Student loans</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                type="number"
                placeholder="0"
                {...register('monthly_debt_student', {
                  min: { value: 0, message: 'Cannot be negative' },
                  valueAsNumber: true,
                })}
              />
            </div>
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label>Credit card minimums</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                type="number"
                placeholder="0"
                {...register('monthly_debt_credit', {
                  min: { value: 0, message: 'Cannot be negative' },
                  valueAsNumber: true,
                })}
              />
            </div>
          </div>
          <div className={styles.field}>
            <label>Other monthly debt</label>
            <div className={styles.inputPrefix}>
              <span>$</span>
              <input
                type="number"
                placeholder="0"
                {...register('monthly_debt_other', {
                  min: { value: 0, message: 'Cannot be negative' },
                  valueAsNumber: true,
                })}
              />
            </div>
          </div>
        </div>

        <p className={styles.sectionLabel}>Credit &amp; location</p>

        <div className={styles.field}>
          <label>Credit score</label>
          <select {...register('credit_score', { valueAsNumber: true })}>
            {CREDIT_SCORE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label>Where do you want to buy?</label>
          <input
            type="text"
            placeholder="78701 or Austin, TX"
            {...register('zip_code', { required: 'Required' })}
          />
          {errors.zip_code && <p className={styles.error}>{errors.zip_code.message}</p>}
        </div>

        {isLoading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner} />
            <span>Calculating your affordability…</span>
          </div>
        ) : (
          <button className={styles.submitBtn} type="submit">
            See my homes →
          </button>
        )}
      </form>
    </div>
  )
}

// ── Step 3 — Results ────────────────────────────────────────────────────────

function Step3({
  result,
  financialData,
}: {
  result: AffordabilityResult
  financialData: FinancialData
}) {
  const navigate = useNavigate()

  const monthlyDebt =
    (financialData.monthly_debt_car ?? 0) +
    (financialData.monthly_debt_student ?? 0) +
    (financialData.monthly_debt_credit ?? 0) +
    (financialData.monthly_debt_other ?? 0)

  const summaryText = `With an annual income of ${fmt(financialData.annual_income)}, ${fmt(result.down_payment)} down, and ${fmt(monthlyDebt)}/mo in existing debt, you qualify for a ${fmtRate(result.rate_used)} mortgage. Your estimated monthly payment would be ${fmt(result.monthly_payment)}. If rates rise 0.5%, your budget shifts by ${fmt(Math.abs(result.buying_power_change_per_half_point))}.`

  return (
    <div className={styles.card}>
      <h1 className={styles.resultsHeadline}>
        You can afford homes up to{' '}
        <span className={styles.priceHighlight}>{fmt(result.max_price)}</span>
      </h1>
      <p className={styles.resultsMeta}>
        Based on your income, {fmtRate(result.rate_used)} rate, and {fmt(result.down_payment)} down
      </p>

      <p className={styles.resultsSummary}>{summaryText}</p>

      <div className={styles.statsRow}>
        <div className={styles.statBox}>
          <span className={styles.statLabel}>Max loan</span>
          <span className={styles.statValue}>{fmt(result.max_loan)}</span>
        </div>
        <div className={styles.statBox}>
          <span className={styles.statLabel}>Monthly payment</span>
          <span className={styles.statValue}>{fmt(result.monthly_payment)}</span>
        </div>
        <div className={styles.statBox}>
          <span className={styles.statLabel}>Rate used</span>
          <span className={styles.statValue}>{fmtRate(result.rate_used)}</span>
        </div>
      </div>

      <button
        className={styles.exploreBtn}
        onClick={() =>
          navigate('/map', { state: { maxPrice: result.max_price, fromOnboarding: true } })
        }
      >
        Explore homes on the map →
      </button>

      <Link to="/dashboard" className={styles.dashboardLink}>
        Go to my dashboard →
      </Link>
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

export default function Onboarding() {
  const [step, setStep] = useState<Step>(1)
  const [affordabilityResult, setAffordabilityResult] = useState<AffordabilityResult | null>(null)
  const [financialData, setFinancialData] = useState<FinancialData | null>(null)

  function handleStep1Success() {
    setStep(2)
  }

  function handleStep2Success(result: AffordabilityResult, data: FinancialData) {
    setAffordabilityResult(result)
    setFinancialData(data)
    setStep(3)
  }

  return (
    <div className={styles.page}>
      <StepIndicator current={step} />

      {step === 1 && <Step1 onSuccess={handleStep1Success} />}
      {step === 2 && <Step2 onSuccess={handleStep2Success} />}
      {step === 3 && affordabilityResult && financialData && (
        <Step3 result={affordabilityResult} financialData={financialData} />
      )}
    </div>
  )
}
