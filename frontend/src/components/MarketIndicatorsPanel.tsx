import type { MarketIndicators } from '../types'
import styles from './MarketIndicatorsPanel.module.css'

interface Props {
  indicators: MarketIndicators
}

function StatRow({
  label,
  value,
  unit,
  trend,
}: {
  label: string
  value: number | null
  unit?: string
  trend?: 'up-bad' | 'up-good' | 'down-bad' | 'down-good' | null
}) {
  const display = value == null ? '—' : `${value.toFixed(2)}${unit ?? ''}`
  return (
    <div className={styles.row}>
      <span className={styles.rowLabel}>{label}</span>
      <span className={`${styles.rowValue} ${trend ? styles[trend] : ''}`}>{display}</span>
    </div>
  )
}

export default function MarketIndicatorsPanel({ indicators }: Props) {
  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Market Signals</h3>

      <div className={styles.stats}>
        <StatRow
          label="30yr Mortgage Rate"
          value={indicators.mortgage_rate}
          unit="%"
        />
        <StatRow
          label="Unemployment"
          value={indicators.unemployment}
          unit="%"
        />
        <StatRow
          label="CPI (Inflation)"
          value={indicators.cpi_yoy}
          unit=" index"
        />
        <StatRow
          label="State GDP Growth"
          value={indicators.gdp_growth}
          unit="%"
        />
      </div>

      {indicators.policy_notes.length > 0 && (
        <div className={styles.policySection}>
          <h4 className={styles.policyHeading}>Policy Context</h4>
          <ul className={styles.policyList}>
            {indicators.policy_notes.map((note, i) => (
              <li key={i} className={styles.policyNote}>
                <span className={styles.policyDot} />
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className={styles.disclaimer}>
        Sources: FRED, BLS, BEA, HUD, MIT Election Lab. Updated monthly.
      </p>
    </div>
  )
}
