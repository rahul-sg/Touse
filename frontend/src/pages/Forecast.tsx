import { useParams, Link } from 'react-router-dom'
import ForecastChart from '../components/ForecastChart'
import MarketIndicatorsPanel from '../components/MarketIndicatorsPanel'
import { useForecast } from '../hooks/useForecast'
import { useMarket } from '../hooks/useMarket'
import styles from './Forecast.module.css'

function fmt(n: number | null) {
  if (n == null) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtTrend(n: number | null) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

export default function Forecast() {
  const { metroId } = useParams<{ metroId: string }>()
  const { data: forecast, isLoading: forecastLoading, isError: forecastError } = useForecast(metroId ?? null)
  const { data: market, isLoading: marketLoading } = useMarket(metroId ?? null)

  const metroName = metroId
    ? metroId.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : ''

  const trend3m = forecast?.trend_3m ?? null
  const trend12m = forecast?.trend_12m ?? null

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link to="/">Home</Link>
          <span>/</span>
          <span>Forecast</span>
        </div>

        <h1 className={styles.title}>{metroName || 'Metro Forecast'}</h1>

        <div className={styles.statShelf}>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>Median Price</p>
            <p className={`${styles.statCellValue} ${styles.brass}`}>
              {fmt(forecast?.current_median_price ?? null)}
            </p>
          </div>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>3-Month Trend</p>
            <p className={`${styles.statCellValue} ${trend3m == null ? '' : trend3m >= 0 ? styles.up : styles.down}`}>
              {fmtTrend(trend3m)}
            </p>
          </div>
          <div className={styles.statCell}>
            <p className={styles.statCellLabel}>12-Month Trend</p>
            <p className={`${styles.statCellValue} ${trend12m == null ? '' : trend12m >= 0 ? styles.up : styles.down}`}>
              {fmtTrend(trend12m)}
            </p>
          </div>
          {forecast?.trained_at && (
            <div className={styles.statCell} style={{ flex: '0 0 auto' }}>
              <p className={styles.statCellLabel}>Model</p>
              <p className={styles.statCellSub}>
                {forecast.model_version ?? '—'}<br />
                Trained {new Date(forecast.trained_at).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>
      </header>

      {forecastError && (
        <div className={styles.error}>
          Could not load forecast for this metro. It may not exist in the database yet.
        </div>
      )}

      <div className={styles.body}>
        <section className={styles.chartSection}>
          <h2 className={styles.sectionTitle}>12-Month Price Forecast</h2>
          <p className={styles.sectionSub}>
            Shaded area shows 80% confidence interval. Dashed line marks today's median.
          </p>

          {forecastLoading ? (
            <div className={styles.loading}><div className={styles.spinner} /></div>
          ) : (
            <ForecastChart
              forecast={forecast?.forecast_12m ?? []}
              currentPrice={forecast?.current_median_price ?? null}
            />
          )}

          {forecast?.top_drivers && Object.keys(forecast.top_drivers).length > 0 && (
            <div className={styles.drivers}>
              <h3 className={styles.driversTitle}>Key Inflection Points</h3>
              <div className={styles.driversGrid}>
                {forecast.top_drivers.strongest_growth_periods?.length > 0 && (
                  <div className={styles.driverGroup}>
                    <span className={styles.driverLabel}>Strongest growth</span>
                    <div className={styles.driverTags}>
                      {forecast.top_drivers.strongest_growth_periods.map((m: string) => (
                        <span key={m} className={`${styles.tag} ${styles.tagUp}`}>{m}</span>
                      ))}
                    </div>
                  </div>
                )}
                {forecast.top_drivers.strongest_decline_periods?.length > 0 && (
                  <div className={styles.driverGroup}>
                    <span className={styles.driverLabel}>Sharpest declines</span>
                    <div className={styles.driverTags}>
                      {forecast.top_drivers.strongest_decline_periods.map((m: string) => (
                        <span key={m} className={`${styles.tag} ${styles.tagDown}`}>{m}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        <aside className={styles.sidebar}>
          {marketLoading ? (
            <div className={styles.loading}><div className={styles.spinner} /></div>
          ) : market ? (
            <MarketIndicatorsPanel indicators={market} />
          ) : null}

          <div className={styles.mapLink}>
            <Link to={`/map`} className={styles.mapLinkBtn}>
              Browse listings in this area →
            </Link>
          </div>
        </aside>
      </div>
    </div>
  )
}
