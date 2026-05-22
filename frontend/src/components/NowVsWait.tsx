import { useState, useCallback } from 'react'
import { compareNowVsWait } from '../utils/api'
import type { NowVsWaitResult } from '../types'
import styles from './NowVsWait.module.css'

/** Minimal financial shape — satisfied by both UserProfile and Scenario. */
export interface NowVsWaitInputs {
  annual_income: number | null
  savings: number | null
  down_payment: number | null
  credit_score: number | null
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string | null
  monthly_take_home?: number | null
}

interface Props {
  profile: NowVsWaitInputs
  loanType?: string
}

const DEFAULT_WAIT_MONTHS = 12

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtDelta(n: number) {
  const sign = n >= 0 ? '+' : ''
  return `${sign}${fmt(n)}`
}

const REC_CONFIG = {
  buy_now: { label: 'Consider buying now', color: 'var(--color-forest)' },
  wait: { label: 'Waiting may help', color: 'var(--color-brass)' },
  neutral: { label: 'Either path works', color: 'var(--color-text-secondary)' },
}

export default function NowVsWait({ profile, loanType }: Props) {
  const monthlyDebt =
    (profile.monthly_debt_car ?? 0) +
    (profile.monthly_debt_student ?? 0) +
    (profile.monthly_debt_credit ?? 0) +
    (profile.monthly_debt_other ?? 0)

  const defaultSavings = profile.monthly_take_home
    ? Math.max(0, Math.round(profile.monthly_take_home * 0.25))
    : 500

  const [monthlySavings, setMonthlySavings] = useState(defaultSavings)
  const [inputVal, setInputVal] = useState(String(defaultSavings))
  const [waitMonths, setWaitMonths] = useState(DEFAULT_WAIT_MONTHS)
  const [waitInput, setWaitInput] = useState(String(DEFAULT_WAIT_MONTHS))
  const [result, setResult] = useState<NowVsWaitResult | null>(null)
  const [resultMonths, setResultMonths] = useState(DEFAULT_WAIT_MONTHS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const profileIncomplete = !profile.annual_income || !profile.down_payment || !profile.credit_score

  const run = useCallback(async (savings: number, months: number) => {
    if (!profile.annual_income || !profile.down_payment || !profile.credit_score) return
    setLoading(true)
    setError(false)
    try {
      const data = await compareNowVsWait({
        annual_income: profile.annual_income,
        monthly_debt: monthlyDebt,
        credit_score: profile.credit_score,
        down_payment: profile.down_payment,
        savings: profile.savings ?? 0,
        zip_code: profile.zip_code ?? '',
        loan_type: loanType ?? 'conventional',
        monthly_savings: savings,
        wait_months: months,
      })
      setResult(data)
      setResultMonths(months)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [profile, monthlyDebt, loanType])

  function handleSavingsChange(val: string) {
    setInputVal(val)
    const n = Number(val)
    if (!isNaN(n) && n >= 0) setMonthlySavings(n)
  }

  function handleWaitChange(val: string) {
    setWaitInput(val)
    const n = Number(val)
    if (!isNaN(n) && n >= 1 && n <= 60) setWaitMonths(n)
  }

  function handleRun() {
    run(monthlySavings, waitMonths)
  }

  function handleReset() {
    setResult(null)
    setError(false)
    setMonthlySavings(defaultSavings)
    setInputVal(String(defaultSavings))
    setWaitMonths(DEFAULT_WAIT_MONTHS)
    setWaitInput(String(DEFAULT_WAIT_MONTHS))
  }

  const rec = result ? REC_CONFIG[result.recommendation] : null

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.title}>Buy now vs wait {waitMonths} months</h2>
        <p className={styles.subtitle}>
          See how your budget changes if you keep saving before buying.
        </p>
      </div>

      <div className={styles.inputRow}>
        <div>
          <label className={styles.inputLabel}>Monthly savings rate</label>
          <div className={styles.inputWrap}>
            <span className={styles.prefix}>$</span>
            <input
              type="number"
              min="0"
              className={styles.input}
              value={inputVal}
              onChange={e => handleSavingsChange(e.target.value)}
              placeholder="2000"
            />
            <span className={styles.suffix}>/mo</span>
          </div>
        </div>

        <div>
          <label className={styles.inputLabel}>Wait period</label>
          <div className={styles.inputWrap}>
            <input
              type="number"
              min="1"
              max="60"
              className={styles.input}
              value={waitInput}
              onChange={e => handleWaitChange(e.target.value)}
              placeholder="12"
            />
            <span className={styles.suffix}>months</span>
          </div>
        </div>

        <button
          className={styles.runBtn}
          onClick={handleRun}
          disabled={loading || profileIncomplete}
          title={profileIncomplete ? 'Complete your financial profile to use this tool' : undefined}
        >
          {loading ? 'Calculating…' : 'Compare →'}
        </button>

        {result && (
          <button className={styles.resetBtn} onClick={handleReset}>
            Reset
          </button>
        )}
      </div>

      {profileIncomplete && (
        <p className={styles.errorMsg}>
          Complete your financial profile (income, down payment, credit score) to use this comparison.
        </p>
      )}

      {!profileIncomplete && error && (
        <p className={styles.errorMsg}>Could not run comparison. Please try again.</p>
      )}

      {result && (
        <>
          {/* Recommendation badge */}
          <div className={styles.recBadge} style={{ borderColor: rec!.color, color: rec!.color }}>
            {rec!.label}
          </div>

          {/* Side-by-side */}
          <div className={styles.comparison}>
            <div className={styles.col}>
              <p className={styles.colLabel}>Buy now</p>
              <p className={styles.colPrice}>{fmt(result.now.max_price)}</p>
              <p className={styles.colSub}>{fmt(result.now.monthly_payment)}/mo · {result.now.rate_used.toFixed(2)}% rate</p>
              <p className={styles.colSub}>Down: {fmt(result.now.down_payment)}</p>
            </div>

            <div className={styles.divider}>→</div>

            <div className={styles.col}>
              <p className={styles.colLabel}>After {resultMonths} months (rates flat)</p>
              <p className={`${styles.colPrice} ${result.price_delta_flat >= 0 ? styles.colPriceUp : styles.colPriceDown}`}>
                {fmt(result.wait.flat.max_price)}
              </p>
              <p className={styles.colSub}>{fmt(result.wait.flat.monthly_payment)}/mo · {result.wait.flat.rate_used.toFixed(2)}% rate</p>
              <p className={styles.colSub}>Down: {fmt(result.wait.flat.down_payment)} ({fmtDelta(result.additional_savings)})</p>
            </div>
          </div>

          {/* Delta bar */}
          <div className={styles.deltaRow}>
            <span className={styles.deltaLabel}>Budget change (flat rates)</span>
            <span className={`${styles.deltaVal} ${result.price_delta_flat >= 0 ? styles.deltaPos : styles.deltaNeg}`}>
              {fmtDelta(result.price_delta_flat)}
            </span>
          </div>

          {/* Rate scenarios */}
          <div className={styles.scenarios}>
            <p className={styles.scenariosLabel}>If rates shift in {resultMonths} months</p>
            <div className={styles.scenarioRow}>
              <span className={styles.scenarioName}>Rates drop 0.5%</span>
              <span className={styles.scenarioRate}>{result.wait.rate_down_half.rate_used.toFixed(2)}%</span>
              <span className={styles.scenarioPrice}>{fmt(result.wait.rate_down_half.max_price)}</span>
              <span className={`${styles.scenarioDelta} ${styles.deltaPos}`}>
                {fmtDelta(result.wait.rate_down_half.max_price - result.now.max_price)}
              </span>
            </div>
            <div className={styles.scenarioRow}>
              <span className={styles.scenarioName}>Rates flat</span>
              <span className={styles.scenarioRate}>{result.wait.flat.rate_used.toFixed(2)}%</span>
              <span className={styles.scenarioPrice}>{fmt(result.wait.flat.max_price)}</span>
              <span className={`${styles.scenarioDelta} ${result.price_delta_flat >= 0 ? styles.deltaPos : styles.deltaNeg}`}>
                {fmtDelta(result.price_delta_flat)}
              </span>
            </div>
            <div className={styles.scenarioRow}>
              <span className={styles.scenarioName}>Rates rise 0.5%</span>
              <span className={styles.scenarioRate}>{result.wait.rate_up_half.rate_used.toFixed(2)}%</span>
              <span className={styles.scenarioPrice}>{fmt(result.wait.rate_up_half.max_price)}</span>
              <span className={`${styles.scenarioDelta} ${result.wait.rate_up_half.max_price - result.now.max_price >= 0 ? styles.deltaPos : styles.deltaNeg}`}>
                {fmtDelta(result.wait.rate_up_half.max_price - result.now.max_price)}
              </span>
            </div>
          </div>

          {/* Factors */}
          {result.factors.length > 0 && (
            <div className={styles.factors}>
              {result.factors.map((f, i) => (
                <p key={i} className={styles.factor}>{f}</p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
