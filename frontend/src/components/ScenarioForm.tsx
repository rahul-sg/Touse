import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useQueryClient } from '@tanstack/react-query'
import { api, createScenario, updateScenario } from '../utils/api'
import type { AffordabilityResult, Scenario, RentalAffordability } from '../types'
import styles from './ScenarioForm.module.css'

interface Props {
  userId: number
  onClose: () => void
  onCreated: (s: Scenario) => void
  /** When provided the form opens in edit mode, pre-populated with this scenario */
  editScenario?: Scenario
}

interface FormValues {
  name: string
  annual_income: number
  savings: number
  down_payment: number
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  credit_score: number
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

type LoanType = 'conventional' | 'fha' | 'va' | 'usda' | 'arm_5_1' | 'jumbo'

const LOAN_TYPES: { value: LoanType; label: string; hint: string }[] = [
  { value: 'conventional', label: 'Conventional', hint: '5% down, 36% DTI' },
  { value: 'fha', label: 'FHA', hint: '3.5% down, 43% DTI' },
  { value: 'va', label: 'VA', hint: '0% down, veterans only' },
  { value: 'usda', label: 'USDA', hint: '0% down, rural only' },
  { value: 'arm_5_1', label: 'ARM 5/1', hint: 'Lower initial rate' },
  { value: 'jumbo', label: 'Jumbo', hint: '>$766k conforming' },
]

export default function ScenarioForm({ userId, onClose, onCreated, editScenario }: Props) {
  const isEdit = Boolean(editScenario)
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'buy' | 'rent'>(
    editScenario?.scenario_type === 'rent' ? 'rent' : 'buy'
  )
  const [loanType, setLoanType] = useState<LoanType>(
    (editScenario?.loan_type as LoanType) ?? 'conventional'
  )
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      name: editScenario?.name ?? '',
      annual_income: editScenario?.annual_income ?? undefined,
      savings: editScenario?.savings ?? undefined,
      down_payment: editScenario?.down_payment ?? undefined,
      monthly_debt_car: editScenario?.monthly_debt_car ?? 0,
      monthly_debt_student: editScenario?.monthly_debt_student ?? 0,
      monthly_debt_credit: editScenario?.monthly_debt_credit ?? 0,
      monthly_debt_other: editScenario?.monthly_debt_other ?? 0,
      credit_score: editScenario?.credit_score ?? 730,
      zip_code: editScenario?.zip_code ?? '',
    },
  })

  async function onSubmit(values: FormValues) {
    setSubmitting(true)
    setSubmitError(null)
    try {
      let cachedMaxPrice: number | undefined
      let cachedMonthlyPayment: number | undefined
      let cachedRateUsed: number | undefined

      const monthlyDebt =
        Number(values.monthly_debt_car) +
        Number(values.monthly_debt_student) +
        Number(values.monthly_debt_credit) +
        Number(values.monthly_debt_other)

      if (mode === 'buy') {
        const { data: aff } = await api.post<AffordabilityResult>('/api/v1/affordability', {
          annual_income: Number(values.annual_income),
          savings: Number(values.savings),
          monthly_debt: monthlyDebt,
          credit_score: Number(values.credit_score),
          down_payment: Number(values.down_payment),
          zip_code: values.zip_code,
          loan_type: loanType,
        })
        cachedMaxPrice = aff.max_price
        cachedMonthlyPayment = aff.monthly_payment
        cachedRateUsed = aff.rate_used
      } else {
        const { data: rental } = await api.post<RentalAffordability>('/api/v1/rental-affordability', {
          annual_income: Number(values.annual_income),
          savings: Number(values.savings),
          monthly_debt_car: Number(values.monthly_debt_car),
          monthly_debt_student: Number(values.monthly_debt_student),
          monthly_debt_credit: Number(values.monthly_debt_credit),
          monthly_debt_other: Number(values.monthly_debt_other),
          credit_score: Number(values.credit_score),
          zip_code: values.zip_code,
        })
        cachedMaxPrice = rental.max_monthly_rent
        cachedMonthlyPayment = rental.recommended_monthly_rent
      }

      const payload = {
        name: values.name,
        scenario_type: mode,
        annual_income: Number(values.annual_income),
        savings: Number(values.savings),
        down_payment: mode === 'buy' ? Number(values.down_payment) : undefined,
        credit_score: Number(values.credit_score),
        monthly_debt_car: Number(values.monthly_debt_car),
        monthly_debt_student: Number(values.monthly_debt_student),
        monthly_debt_credit: Number(values.monthly_debt_credit),
        monthly_debt_other: Number(values.monthly_debt_other),
        zip_code: values.zip_code,
        loan_type: mode === 'buy' ? loanType : undefined,
        cached_max_price: cachedMaxPrice,
        cached_monthly_payment: cachedMonthlyPayment,
        cached_rate_used: cachedRateUsed,
      }

      const scenario = isEdit && editScenario
        ? await updateScenario(editScenario.id, payload)
        : await createScenario(userId, payload)

      // Invalidate the scenarios cache so ScenarioDetail re-renders with fresh data
      await queryClient.invalidateQueries({ queryKey: ['scenarios', userId] })

      onCreated(scenario)
      onClose()
    } catch {
      setSubmitError('Something went wrong. Please check your inputs and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
        <h2 className={styles.title}>{isEdit ? 'Edit scenario' : 'New scenario'}</h2>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${mode === 'buy' ? styles.tabActive : ''}`}
            onClick={() => setMode('buy')}
          >
            Buy
          </button>
          <button
            type="button"
            className={`${styles.tab} ${mode === 'rent' ? styles.tabActive : ''}`}
            onClick={() => setMode('rent')}
          >
            Rent
          </button>
        </div>

        {/* Loan type selector — buy only */}
        {mode === 'buy' && (
          <div className={styles.loanTypeSection}>
            <p className={styles.loanTypeLabel}>Loan type</p>
            <div className={styles.loanTypeGrid}>
              {LOAN_TYPES.map(lt => (
                <button
                  key={lt.value}
                  type="button"
                  className={`${styles.loanTypeBtn} ${loanType === lt.value ? styles.loanTypeBtnActive : ''}`}
                  onClick={() => setLoanType(lt.value)}
                >
                  <span className={styles.loanTypeName}>{lt.label}</span>
                  <span className={styles.loanTypeHint}>{lt.hint}</span>
                </button>
              ))}
            </div>
            {loanType === 'arm_5_1' && (
              <p className={styles.loanTypeWarning}>
                ARM rates adjust after 5 years — your max payment shown is the initial rate.
                We will also show your worst-case payment at the rate cap.
              </p>
            )}
            {loanType === 'va' && (
              <p className={styles.loanTypeInfo}>
                VA loans require military service eligibility. A 2.15% funding fee is financed into the loan.
              </p>
            )}
            {loanType === 'usda' && (
              <p className={styles.loanTypeInfo}>
                USDA loans are limited to rural and suburban areas with income limits. A 1% upfront fee applies.
              </p>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className={styles.fields}>
          {/* Name */}
          <div className={styles.field}>
            <label>Scenario name</label>
            <input
              {...register('name', { required: true })}
              placeholder={mode === 'buy' ? 'e.g. Conservative buy' : 'e.g. 1BR rental budget'}
            />
            {errors.name && <span className={styles.error}>Name is required</span>}
          </div>

          {/* Income & Savings */}
          <div className={styles.row}>
            <div className={styles.field}>
              <label>Annual income</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input
                  type="number"
                  min="0"
                  {...register('annual_income', { required: true, min: 1 })}
                  placeholder="95000"
                />
              </div>
              {errors.annual_income && <span className={styles.error}>Required</span>}
            </div>
            <div className={styles.field}>
              <label>Total savings</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input
                  type="number"
                  min="0"
                  {...register('savings', { required: true, min: 0 })}
                  placeholder="60000"
                />
              </div>
              {errors.savings && <span className={styles.error}>Required</span>}
            </div>
          </div>

          {/* Down payment — buy only */}
          {mode === 'buy' && (
            <div className={styles.field}>
              <label>Down payment available</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input
                  type="number"
                  min="0"
                  {...register('down_payment', { required: mode === 'buy', min: 0 })}
                  placeholder="80000"
                />
              </div>
              {errors.down_payment && <span className={styles.error}>Required for buy scenarios</span>}
            </div>
          )}

          {/* Monthly debts */}
          <p className={styles.sectionLabel}>Monthly debts</p>
          <div className={styles.row}>
            <div className={styles.field}>
              <label>Car payment</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input type="number" min="0" {...register('monthly_debt_car')} placeholder="0" />
              </div>
            </div>
            <div className={styles.field}>
              <label>Student loans</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input type="number" min="0" {...register('monthly_debt_student')} placeholder="0" />
              </div>
            </div>
          </div>
          <div className={styles.row}>
            <div className={styles.field}>
              <label>Credit card min.</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input type="number" min="0" {...register('monthly_debt_credit')} placeholder="0" />
              </div>
            </div>
            <div className={styles.field}>
              <label>Other debt</label>
              <div className={styles.inputWrap}>
                <span className={styles.prefix}>$</span>
                <input type="number" min="0" {...register('monthly_debt_other')} placeholder="0" />
              </div>
            </div>
          </div>

          {/* Credit score */}
          <div className={styles.field}>
            <label>Credit score range</label>
            <select {...register('credit_score', { required: true })}>
              {CREDIT_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {errors.credit_score && <span className={styles.error}>Required</span>}
          </div>

          {/* ZIP */}
          <div className={styles.field}>
            <label>ZIP code</label>
            <input
              {...register('zip_code', { required: true })}
              placeholder="78701"
              maxLength={10}
            />
            {errors.zip_code && <span className={styles.error}>Required</span>}
          </div>

          {submitError && <p className={styles.error}>{submitError}</p>}

          <button type="submit" className={styles.submitBtn} disabled={submitting}>
            {submitting ? 'Recalculating…' : isEdit ? `Recalculate & save` : `Calculate & save ${mode} scenario`}
          </button>
        </form>
      </div>
    </div>
  )
}
