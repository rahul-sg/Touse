import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ForecastChart from '../components/ForecastChart'
import { getZipForecast, getZipProjection, getMarketContext } from '../utils/api'
import type { ZipProjection, MarketContext } from '../utils/api'
import type { ForecastPoint } from '../types'
import styles from './Forecast.module.css'

// ── Rate scenarios ───────────────────────────────────────────────────────────
// The Prophet model is univariate — it cannot see interest rates. These
// scenarios apply a transparent, illustrative price elasticity so users can
// see rate risk; they are NOT a rate-adjusted prediction from the model.

type RateScenario = 'base' | 'up' | 'down'

/** Illustrative price response per 1 percentage point of rate change, by month 12. */
const RATE_ELASTICITY = 0.04
const FORECAST_HORIZON = 12

const RATE_OPTIONS: { value: RateScenario; label: string }[] = [
  { value: 'down', label: 'Rates −1 pt' },
  { value: 'base', label: 'Today’s rates' },
  { value: 'up', label: 'Rates +1 pt' },
]

/**
 * Apply a rate scenario to the projected (future) points. Rates up → prices
 * down. The effect ramps linearly across the 12-month horizon. History points
 * (the leading tail) are left untouched.
 */
function applyRateScenario(points: ForecastPoint[], scenario: RateScenario): ForecastPoint[] {
  if (scenario === 'base' || points.length === 0) return points
  const sign = scenario === 'up' ? -1 : 1
  const firstFuture = Math.max(0, points.length - FORECAST_HORIZON)
  return points.map((p, i) => {
    if (i < firstFuture) return p
    const t = i - firstFuture + 1 // 1..12
    const factor = 1 + sign * RATE_ELASTICITY * (t / FORECAST_HORIZON)
    return {
      month: p.month,
      price: Math.round(p.price * factor),
      lower: Math.round(p.lower * factor),
      upper: Math.round(p.upper * factor),
    }
  })
}

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
  const [rateScenario, setRateScenario] = useState<RateScenario>('base')

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

  const currentValue = projection?.current_value ?? trends?.current_median_value ?? null
  const displayForecast = applyRateScenario(projection?.forecast_12m ?? [], rateScenario)
  const scenarioPct =
    displayForecast.length && currentValue
      ? ((displayForecast[displayForecast.length - 1].price - currentValue) / currentValue) * 100
      : null

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
            Prophet time-series model trained on this ZIP's full price history, blended
            toward the long-run growth rate. Shaded area is the 80% confidence interval;
            the dashed line marks today's value.
          </p>

          {projection && (
            <div className={styles.rateToggle}>
              <span className={styles.rateToggleLabel}>Rate scenario</span>
              <div className={styles.rateBtns}>
                {RATE_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    className={`${styles.rateBtn} ${rateScenario === opt.value ? styles.rateBtnActive : ''}`}
                    onClick={() => setRateScenario(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {projLoading ? (
            <div className={styles.loading}>
              <div className={styles.spinner} />
              <p style={{ marginTop: '0.75rem' }}>Training the forecast model…</p>
            </div>
          ) : (
            <ForecastChart forecast={displayForecast} currentPrice={currentValue} />
          )}

          {projection && scenarioPct != null && (
            <p className={styles.scenarioNote}>
              {rateScenario === 'base'
                ? `The model projects ${fmtTrend(scenarioPct)} over the next 12 months.`
                : `If 30-year rates ${rateScenario === 'up' ? 'rise' : 'fall'} roughly 1 point, this scenario shows about ${fmtTrend(scenarioPct)}.`}
            </p>
          )}

          {projection && (
            <p className={styles.sectionSub} style={{ marginTop: '0.75rem' }}>
              Model: Prophet · trained on {projection.data_points} months of history ·
              last updated {new Date(projection.trained_at).toLocaleDateString()}. Rate
              scenarios apply an illustrative {Math.round(RATE_ELASTICITY * 100)}% price
              response per point of rate change — the model itself does not forecast rates.
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
