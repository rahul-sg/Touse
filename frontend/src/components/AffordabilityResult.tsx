import type { AffordabilityResult as Result } from '../types'
import styles from './AffordabilityResult.module.css'

interface Props {
  result: Result
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function AffordabilityResult({ result }: Props) {
  const rateShiftPositive = result.buying_power_change_per_half_point >= 0
  const rateShiftLabel = rateShiftPositive
    ? `+${fmt(Math.abs(result.buying_power_change_per_half_point))}`
    : `−${fmt(Math.abs(result.buying_power_change_per_half_point))}`

  return (
    <div className={styles.card}>
      <div className={styles.hero}>
        <p className={styles.heroLabel}>You can afford up to</p>
        <p className={styles.heroPrice}>{fmt(result.max_price)}</p>
        <p className={styles.heroSub}>
          {fmt(result.monthly_payment)}/mo · {result.rate_used}% rate · {fmt(result.down_payment)} down
        </p>
      </div>

      <div className={styles.breakdown}>
        <StatItem label="Max Loan" value={fmt(result.max_loan)} />
        <StatItem label="Monthly Payment" value={`${fmt(result.monthly_payment)}/mo`} />
        <StatItem label="Rate Used" value={`${result.rate_used}%`} />
      </div>

      <div className={styles.rateAlert}>
        <p>
          If rates shift +0.5%, your buying power changes by{' '}
          <strong>{rateShiftLabel}</strong>
        </p>
      </div>
    </div>
  )
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.statItem}>
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue}>{value}</p>
    </div>
  )
}
