import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ForecastChart from '../components/ForecastChart'
import { getZipForecast, getZipProjection, getMarketContext } from '../utils/api'
import type { ZipProjection, MarketContext } from '../utils/api'
import styles from './Forecast.module.css'

function fmt(n: number | null) {
  if (n == null) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtTrend(n: number | null | undefined) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function fmtPct(n: number | null | undefined) {
  if (n == null) return '—'
  return `${n.toFixed(n % 1 === 0 ? 0 : 1)}%`
}

interface ZipTrends {
  zip_code: string
  city: string | null
  state: string | null
  metro: string | null
  current_median_value: number
  as_of: string
  trend_3m_pct: number | null
  trend_12m_pct: number | null
  direction: string
}

export default function Forecast() {
  const { zip } = useParams<{ zip: string }>()

  const [trends, setTrends] = useState<ZipTrends | null>(null)
  const [projection, setProjection] = useState<ZipProjection | null>(null)
  const [marketContext, setMarketContext] = useState<MarketContext | null>(null)
  const [trendsLoading, setTrendsLoading] = useState(true)
  const [projLoading, setProjLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!zip) return
    setTrendsLoading(true)
    setProjLoading(true)
    setError(null)
    setTrends(null)
    setProjection(null)
    setMarketContext(null)

    getZipForecast(zip)
      .then(setTrends)
      .catch(() => setError('No price history is available for this ZIP code yet.'))
      .finally(() => setTrendsLoading(false))

    // The projection trains a Prophet model on first request (a few seconds).
    getZipProjection(zip)
      .then(setProjection)
      .catch(() => setProjection(null))
      .finally(() => setProjLoading(false))

    getMarketContext(zip)
      .then(setMarketContext)
      .catch(() => setMarketContext(null))
  }, [zip])

  const place = trends ? [trends.city, trends.state].filter(Boolean).join(', ') : ''
  const proj12m = projection?.forecast_12m_pct ?? null

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link to="/dashboard">Dashboard</Link>
          <span>/</span>
          <span>ZIP forecast</span>
        </div>

        <h1 className={styles.title}>{place || `ZIP ${zip}`}</h1>

        <div className={styles.statShelf}>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>Median Home Value</p>
            <p className={`${styles.statCellValue} ${styles.brass}`}>
              {fmt(trends?.current_median_value ?? null)}
            </p>
          </div>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>3-Month Trend</p>
            <p className={`${styles.statCellValue} ${trends?.trend_3m_pct == null ? '' : trends.trend_3m_pct >= 0 ? styles.up : styles.down}`}>
              {fmtTrend(trends?.trend_3m_pct)}
            </p>
          </div>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>12-Month Trend</p>
            <p className={`${styles.statCellValue} ${trends?.trend_12m_pct == null ? '' : trends.trend_12m_pct >= 0 ? styles.up : styles.down}`}>
              {fmtTrend(trends?.trend_12m_pct)}
            </p>
          </div>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>Projected (next 12mo)</p>
            <p className={`${styles.statCellValue} ${proj12m == null ? '' : proj12m >= 0 ? styles.up : styles.down}`}>
              {projLoading ? '…' : fmtTrend(proj12m)}
            </p>
          </div>
        </div>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.body}>
        <section className={styles.chartSection}>
          <h2 className={styles.sectionTitle}>12-Month Price Forecast</h2>
          <p className={styles.sectionSub}>
            Prophet time-series model trained on this ZIP's full price history.
            Shaded area is the 80% confidence interval; the dashed line marks today's value.
          </p>

          {projLoading ? (
            <div className={styles.loading}>
              <div className={styles.spinner} />
              <p style={{ marginTop: '0.75rem' }}>Training the forecast model…</p>
            </div>
          ) : (
            <ForecastChart
              forecast={projection?.forecast_12m ?? []}
              currentPrice={projection?.current_value ?? trends?.current_median_value ?? null}
            />
          )}

          {projection && (
            <p className={styles.sectionSub} style={{ marginTop: '1rem' }}>
              Model: Prophet · trained on {projection.data_points} months of history ·
              last updated {new Date(projection.trained_at).toLocaleDateString()}.
            </p>
          )}
        </section>

        <aside className={styles.sidebar}>
          {marketContext && (
            <div className={styles.contextCard}>
              <h3 className={styles.contextTitle}>Market Context</h3>
              <div className={styles.contextRow}>
                <span className={styles.contextLabel}>30-yr mortgage rate</span>
                <span className={styles.contextValue}>{fmtPct(marketContext.mortgage_rate_30y)}</span>
              </div>
              <div className={styles.contextRow}>
                <span className={styles.contextLabel}>Inflation (CPI, year-over-year)</span>
                <span className={styles.contextValue}>{fmtPct(marketContext.cpi_yoy_pct)}</span>
              </div>
              <div className={styles.contextRow}>
                <span className={styles.contextLabel}>US unemployment</span>
                <span className={styles.contextValue}>{fmtPct(marketContext.unemployment_pct)}</span>
              </div>
              {marketContext.state_gdp_growth_pct != null && (
                <div className={styles.contextRow}>
                  <span className={styles.contextLabel}>
                    {marketContext.state_code} GDP growth
                    {marketContext.state_gdp_year ? ` (${marketContext.state_gdp_year})` : ''}
                  </span>
                  <span className={`${styles.contextValue} ${marketContext.state_gdp_growth_pct >= 0 ? styles.up : styles.down}`}>
                    {fmtTrend(marketContext.state_gdp_growth_pct)}
                  </span>
                </div>
              )}
              <p className={styles.contextNote}>
                National figures from FRED &amp; Freddie Mac; state GDP from the BEA.
              </p>
            </div>
          )}

          <div className={styles.mapLink}>
            <Link
              to="/map"
              state={zip ? { targetZip: zip } : undefined}
              className={styles.mapLinkBtn}
            >
              Browse listings in {place || `ZIP ${zip}`} →
            </Link>
          </div>
        </aside>
      </div>

      {trendsLoading && !trends && !error && (
        <div className={styles.loading}><div className={styles.spinner} /></div>
      )}
    </div>
  )
}
