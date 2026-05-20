import { useForm } from 'react-hook-form'
import type { AffordabilityInput } from '../hooks/useAffordability'
import styles from './AffordabilityForm.module.css'

interface Props {
  onSubmit: (data: AffordabilityInput) => void
  isLoading: boolean
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

export default function AffordabilityForm({ onSubmit, isLoading }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AffordabilityInput>({
    defaultValues: {
      annual_income: undefined,
      savings: undefined,
      monthly_debt: 0,
      credit_score: 800,
      down_payment: undefined,
      zip_code: '',
    },
  })

  return (
    <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
      <div className={styles.grid}>
        <div className={styles.field}>
          <label>Annual Income</label>
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
          <label>Down Payment</label>
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
          {errors.down_payment && <p className={styles.error}>{errors.down_payment.message}</p>}
        </div>

        <div className={styles.field}>
          <label>Monthly Debt Payments</label>
          <div className={styles.inputPrefix}>
            <span>$</span>
            <input
              type="number"
              placeholder="400"
              {...register('monthly_debt', {
                required: 'Required',
                min: { value: 0, message: 'Cannot be negative' },
                valueAsNumber: true,
              })}
            />
          </div>
          <p className={styles.hint}>Car loans, student loans, credit cards</p>
          {errors.monthly_debt && <p className={styles.error}>{errors.monthly_debt.message}</p>}
        </div>

        <div className={styles.field}>
          <label>Savings</label>
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
          <label>Credit Score</label>
          <select {...register('credit_score', { valueAsNumber: true })}>
            {CREDIT_SCORE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label>ZIP Code</label>
          <input
            type="text"
            placeholder="78701"
            maxLength={5}
            {...register('zip_code', {
              required: 'Required',
              pattern: { value: /^\d{5}$/, message: 'Enter a valid 5-digit ZIP' },
            })}
          />
          {errors.zip_code && <p className={styles.error}>{errors.zip_code.message}</p>}
        </div>
      </div>

      <button className={styles.submit} type="submit" disabled={isLoading}>
        {isLoading ? 'Calculating…' : 'Calculate My Budget'}
      </button>
    </form>
  )
}
