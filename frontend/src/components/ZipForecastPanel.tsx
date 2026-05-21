import { useEffect, useState } from 'react'
import { getZipForecast } from '../utils/api'
import styles from './ZipForecastPanel.module.css'

interface ZipForecast {
  zip_code: string
  city: string | null
  state: string | null
  metro: string | null
  current_median_value: number
  as_of: string
  trend_3m_pct: number | null
  trend_6m_pct: number | null
  trend_12m_pct: number | null
  direction: string
  data_points: number
}

interface Props {
  zip: string
}

function fmtTrend(pct: number | null): string {
  if (pct === null) return '—'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}

function TrendBadge({ pct }: { pct: number | null }) {
  if (pct === null) return <span className={styles.trendNeutral}>—</span>
  if (pct > 1) return <span className={styles.trendUp}>{fmtTrend(pct)}</span>
  if (pct < -1) return <span className={styles.trendDown}>{fmtTrend(pct)}</span>
  return <span className={styles.trendNeutral}>{fmtTrend(pct)}</span>
}

export default function ZipForecastPanel({ zip }: Props) {
  const [data, setData] = useState<ZipForecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    setLoading(true)
    setMissing(false)
    setData(null)
    getZipForecast(zip)
      .then(setData)
      .catch(() => setMissing(true))
      .finally(() => setLoading(false))
  }, [zip])

  if (loading) return <div className={styles.loading}>Loading ZIP data…</div>
  if (missing || !data) {
    return (
      <div className={styles.missing}>
        No price history for {zip} yet.{' '}
        <span className={styles.missingHint}>Run the Zillow ZIP ETL to populate data.</span>
      </div>
    )
  }

  const directionClass =
    data.direction === 'rising' ? styles.dirRising :
    data.direction === 'falling' ? styles.dirFalling : styles.dirFlat

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.zip}>{data.zip_code}</span>
        {data.city && <span className={styles.city}>{data.city}{data.state ? `, ${data.state}` : ''}</span>}
        <span className={`${styles.direction} ${directionClass}`}>{data.direction}</span>
      </div>

      <div className={styles.price}>
        {data.current_median_value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
        <span className={styles.priceSub}>median home value</span>
      </div>

      <div className={styles.trends}>
        <div className={styles.trendCell}>
          <span className={styles.trendLabel}>3-month</span>
          <TrendBadge pct={data.trend_3m_pct} />
        </div>
        <div className={styles.trendCell}>
          <span className={styles.trendLabel}>6-month</span>
          <TrendBadge pct={data.trend_6m_pct} />
        </div>
        <div className={styles.trendCell}>
          <span className={styles.trendLabel}>12-month</span>
          <TrendBadge pct={data.trend_12m_pct} />
        </div>
      </div>

      {data.metro && (
        <p className={styles.metro}>{data.metro}</p>
      )}
      <p className={styles.asOf}>As of {new Date(data.as_of).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</p>
    </div>
  )
}
