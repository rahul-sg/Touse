import { useParams, Link } from 'react-router-dom'
import ForecastChart from '../components/ForecastChart'
import MarketIndicatorsPanel from '../components/MarketIndicatorsPanel'
import TrendBadge from '../components/TrendBadge'
import { useForecast } from '../hooks/useForecast'
import { useMarket } from '../hooks/useMarket'
import styles from './Forecast.module.css'

function fmt(n: number | null) {
  if (n == null) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function Forecast() {
  const { metroId } = useParams<{ metroId: string }>()
  const { data: forecast, isLoading: forecastLoading, isError: forecastError } = useForecast(metroId ?? null)
  const { data: market, isLoading: marketLoading } = useMarket(metroId ?? null)

  const metroName = metroId
    ? metroId.replace(/-/g, ' ').replace(/_/g, ' ').replace(/,/g, ',').replace(/\b\w/g, (c) => c.toUpperCase())
    : ''

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link to="/">Home</Link>
          <span>/</span>
          <span>Forecast</span>
        </div>

        <h1 className={styles.title}>{metroName || 'Metro Forecast'}</h1>

        {forecast && (
          <div className={styles.meta}>
            {forecast.current_median_price != null && (
              <span className={styles.currentPrice}>
                Current median: <strong>{fmt(forecast.current_median_price)}</strong>
              </span>
            )}
            {forecast.trained_at && (
              <span className={styles.trainedAt}>
                Model trained {new Date(forecast.trained_at).toLocaleDateString()}
              </span>
            )}
          </div>
        )}

        <div className={styles.badges}>
          <TrendBadge label="3-Month" value={forecast?.trend_3m ?? null} />
          <TrendBadge label="12-Month" value={forecast?.trend_12m ?? null} />
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
