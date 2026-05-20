import styles from './TrendBadge.module.css'

interface Props {
  label: string
  value: number | null
}

export default function TrendBadge({ label, value }: Props) {
  if (value == null) {
    return (
      <div className={styles.badge}>
        <span className={styles.label}>{label}</span>
        <span className={styles.valueNeutral}>—</span>
      </div>
    )
  }

  const positive = value >= 0
  const sign = positive ? '+' : ''
  return (
    <div className={`${styles.badge} ${positive ? styles.up : styles.down}`}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>
        {positive ? '▲' : '▼'} {sign}{value.toFixed(1)}%
      </span>
    </div>
  )
}
