import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMethodologySummary } from '../utils/api'
import type { MethodologySummary } from '../utils/api'
import styles from './Methodology.module.css'

function fmtInt(n: number): string {
  return n.toLocaleString('en-US')
}

function fmtPct(p: number | null | undefined, signed = false): string {
  if (p === null || p === undefined || Number.isNaN(p)) return '—'
  const v = p * 100
  return `${signed && v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

function fmtMonth(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

const HOME_TYPE_LABEL: Record<string, string> = {
  all: 'All homes',
  single_family: 'Single family',
  condo: 'Condo',
}

export default function Methodology() {
  const [data, setData] = useState<MethodologySummary | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    getMethodologySummary().then(setData).catch(() => setError(true))
  }, [])

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.errorBox}>Could not load methodology data right now.</div>
      </div>
    )
  }
  if (!data) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingBox}>Loading…</div>
      </div>
    )
  }

  const { model, coverage, features, pipeline } = data

  return (
    <div className={styles.page}>
      <p className={styles.eyebrow}>Methodology · deep dive</p>
      <h1 className={styles.title}>How Touse forecasts a home price</h1>
      <p className={styles.lead}>
        This page is the long version of "how the forecast works." If you want the short version,
        the <Link to="/about">About page</Link> has it. Here we walk through the data, the model
        architecture, the math, and the live numbers — including how the model serving your
        forecast right now scored on held-out months.
      </p>

      {/* ── TL;DR ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>The 60-second version</h2>
        <p>
          A 12-month ZIP price forecast comes out of a two-stage pipeline. A <strong>global
          LightGBM panel model</strong> sees every ZIP × home-type × month in Zillow's history with
          lagged prices, US macro, metro supply and rent, and an election-cycle flag — and emits a
          single 12-month growth-rate anchor per (ZIP, home type). A per-(ZIP, home_type){' '}
          <strong>Prophet</strong> time-series model then shapes the monthly trajectory and 80%
          confidence band, with its 12-month endpoint blended heavily toward the LightGBM anchor.
          We retrain monthly on the day after Zillow publishes new ZHVI data, then re-fit cached
          Prophet trajectories so served forecasts always reflect the newest anchor.
        </p>
      </section>

      {/* ── Live model snapshot ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>The model serving forecasts right now</h2>
        <p>
          Every production training run inserts a row into a <code>model_runs</code> audit table.
          This block reads the most recent row — what you see here is what's serving your forecast.
        </p>
        {model ? (
          <>
            <div className={styles.statGrid}>
              <div className={styles.statCell}>
                <p className={styles.statLabel}>Version</p>
                <p className={styles.statValue}>{model.version}</p>
                <p className={styles.statSub}>Trained {fmtDate(model.trained_at)}</p>
              </div>
              <div className={styles.statCell}>
                <p className={styles.statLabel}>Training rows</p>
                <p className={styles.statValue}>{fmtInt(model.train_rows)}</p>
                <p className={styles.statSub}>from {fmtInt(model.panel_rows)} panel rows</p>
              </div>
              <div className={styles.statCell}>
                <p className={styles.statLabel}>Features</p>
                <p className={styles.statValue}>{model.feature_count}</p>
                <p className={styles.statSub}>incl. zip_code &amp; home_type as categoricals</p>
              </div>
              <div className={styles.statCell}>
                <p className={styles.statLabel}>Train time</p>
                <p className={styles.statValue}>{model.train_seconds.toFixed(0)}s</p>
                <p className={styles.statSub}>excludes panel-build time</p>
              </div>
            </div>
            {model.notes && <p className={styles.note}>{model.notes}</p>}
          </>
        ) : (
          <p>No model run recorded yet.</p>
        )}
      </section>

      {/* ── Backtest ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Backtest accuracy</h2>
        <p>
          Every retrain holds out the most recent 12 months that have a known 12-month-ahead price
          and scores the model on a randomly sampled set of ZIPs. Lower MAPE is better; bias near
          zero is better (positive bias = the model systematically over-predicts growth; negative =
          systematic under-prediction).
        </p>
        <p className={styles.subPara}>
          <strong>Why MAPE.</strong> Mean Absolute Percentage Error is scale-invariant — it treats
          a 3% miss on a $400k home the same as a 3% miss on a $2M home. That's the right invariant
          for housing because errors compound geographically; a model that's "great on cheap ZIPs"
          but garbage on expensive ones doesn't help anyone.
        </p>
        <p className={styles.subPara}>
          <strong>Why we report bias separately.</strong> A model can have a respectable MAPE but
          be consistently optimistic — perfectly fine for ranking ZIPs against each other, but
          dangerous for someone deciding whether to buy now. Bias surfaces that.
        </p>
        {model && (model.backtest_mape_all !== null || model.backtest_per_type) ? (
          <div className={styles.metricBlock}>
            <div className={styles.coverageRow}>
              <span className={styles.coverageLabel}>
                <strong>All homes</strong> <span className={styles.dim}>(baseline-comparable slice)</span>
              </span>
              <span className={styles.coverageValue}>
                MAPE {fmtPct(model.backtest_mape_all)} · bias {fmtPct(model.backtest_bias_all, true)}
              </span>
            </div>
            {model.backtest_per_type &&
              Object.entries(model.backtest_per_type)
                .filter(([ht]) => ht !== 'all')
                .map(([ht, m]) => (
                  <div key={ht} className={styles.coverageRow}>
                    <span className={styles.coverageLabel}>{HOME_TYPE_LABEL[ht] ?? ht}</span>
                    <span className={styles.coverageValue}>
                      MAPE {fmtPct(m.mape)} · bias {fmtPct(m.bias, true)} · n={fmtInt(m.n)}
                    </span>
                  </div>
                ))}
          </div>
        ) : (
          <p className={styles.note}>
            No backtest metrics on the current run yet. They populate after the next scheduled
            backtest pass.
          </p>
        )}
        <p className={styles.subPara}>
          <strong>What good looks like.</strong> The prior single-type baseline (Prophet+CAGR
          blend) sat at MAPE ≈ 4.66%. The first LightGBM panel with supply features hit ≈ 3.18%.
          The typed model adds home-type granularity on top of that — the All slice is the
          apples-to-apples number to compare against the prior baselines.
        </p>
      </section>

      {/* ── Pipeline ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>The two-stage pipeline</h2>
        <div className={styles.pipelineStep}>
          <span className={styles.pipelineLabel}>Stage 1</span>
          <p className={styles.pipelineDesc}>{pipeline.stage_1}</p>
        </div>
        <div className={styles.pipelineStep}>
          <span className={styles.pipelineLabel}>Stage 2</span>
          <p className={styles.pipelineDesc}>{pipeline.stage_2}</p>
        </div>
        <div className={styles.pipelineStep}>
          <span className={styles.pipelineLabel}>Fallback</span>
          <p className={styles.pipelineDesc}>{pipeline.fallback}</p>
        </div>
        <p className={styles.subPara} style={{ marginTop: '1rem' }}>
          <strong>Why two stages instead of one model end-to-end.</strong> The two failure modes of
          a price forecast are different problems. The <em>endpoint</em> (where will prices be in
          12 months) is a structural question that benefits from seeing every ZIP at once — rate
          regimes, supply dynamics, regional momentum. The <em>path</em> (how does it get there
          month by month) is a local question that benefits from a model fit to just that ZIP's own
          history and seasonality. We use the right tool for each job and blend them with a
          fixed schedule.
        </p>
        <p className={styles.subPara}>
          <strong>Why we anchor heavily toward the LightGBM endpoint.</strong> Univariate
          time-series models on a single ZIP have a known failure mode: they extrapolate the most
          recent slope linearly. After a boom, that means absurd "house doubles in 5 years"
          forecasts. Anchoring the endpoint to a model that has seen the full national picture
          stops the runaway extrapolation cold.
        </p>
      </section>

      {/* ── Math ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>The math (for the curious)</h2>
        <h3 className={styles.subSectionTitle}>Target</h3>
        <p>
          For each (ZIP, home_type, month) row in the panel, the prediction target is the
          12-month-forward price growth:
        </p>
        <pre className={styles.codeBlock}>target<sub>t</sub> = price<sub>t+12</sub> / price<sub>t</sub> − 1</pre>
        <p>
          Rows without a known 12-month-forward price (the last 12 months of history) are excluded
          from training but kept for prediction at serving time.
        </p>
        <h3 className={styles.subSectionTitle}>Anchoring + blend</h3>
        <p>
          For a given (ZIP, home_type), let <em>g</em> be the LightGBM-predicted 12-month growth
          rate and <em>P<sub>0</sub></em> be the current price. The implied endpoint price is{' '}
          <em>P<sub>12</sub></em>{' '}<code>= P<sub>0</sub> · (1 + g)</code>. We derive a monthly
          growth rate from that endpoint:
        </p>
        <pre className={styles.codeBlock}>r<sub>monthly</sub> = (P<sub>12</sub> / P<sub>0</sub>)<sup>1/12</sup> − 1</pre>
        <p>
          The Prophet trajectory is rescaled so its first projected month starts from{' '}
          <em>P<sub>0</sub></em> (preventing the in-sample/out-of-sample seam), then blended toward
          the anchor path at each future month <em>t</em> ∈ [1..12]:
        </p>
        <pre className={styles.codeBlock}>{`weight(t) = w_near − (w_near − w_far) · (t − 1) / 11
blended(t) = weight(t) · prophet_scaled(t) + (1 − weight(t)) · P_0 · (1 + r_monthly)^t`}</pre>
        <p>
          Defaults are <em>w_near = 0.30</em> at month 1 and <em>w_far = 0.15</em> at month 12 —
          i.e. the anchor dominates throughout. The 80% confidence band is Prophet's, recentered on
          the blended value to preserve its width (in % terms) at each horizon.
        </p>
        <h3 className={styles.subSectionTitle}>Cold-start fallback</h3>
        <p>
          For (ZIP, home_type) combinations the LightGBM panel doesn't have a prediction for —
          typically condo or SFR series that Zillow doesn't publish in that ZIP — we fall back to a{' '}
          <em>20-year CAGR</em> anchor instead:
        </p>
        <pre className={styles.codeBlock}>{`annual_cagr = (P_0 / P_−240)^(1/20) − 1
annual_cagr ∈ [−10%, +6%]  // clamped`}</pre>
        <p>
          The clamps prevent absurd anchors in tiny ZIPs with sparse history.
        </p>
      </section>

      {/* ── Features ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Features</h2>
        <p>
          The LightGBM panel uses {model?.feature_count ?? '~37'} features grouped into five
          buckets. Every feature is computed from public data sources documented on the{' '}
          <Link to="/about">About page</Link>.
        </p>
        {features.map((g) => (
          <div key={g.group} className={styles.featureGroup}>
            <p className={styles.featureGroupTitle}>{g.group}</p>
            <ul className={styles.featureList}>
              {g.items.map((it) => <li key={it}>{it}</li>)}
            </ul>
          </div>
        ))}
        <p className={styles.subPara}>
          <strong>What we deliberately don't include.</strong> Raw sentiment, social-media signals,
          and political-prediction-market prices were considered and dropped — they're noisy
          enough that they hurt held-out MAPE more than they helped. The election-year flag is the
          one political feature that survived backtesting; quantified policy outcomes (housing
          bonds, zoning reform scores) are on the roadmap as a future feature group.
        </p>
        <p className={styles.subPara}>
          <strong>How leakage is prevented.</strong> Lag features are computed{' '}
          <em>within</em> each (zip_code, home_type) group — a condo's history can never leak into
          a single-family lag for the same ZIP. The training/eval split uses time-based holdouts
          (last 12 months of known targets); no random shuffling. Macro features are joined as-of,
          backward — at training time t we only use macro values published at or before t.
        </p>
      </section>

      {/* ── Coverage ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Forecast coverage</h2>
        <p>
          Number of (ZIP, home type) combinations the live LightGBM endpoint model has predictions
          for. Combinations not listed gracefully fall back to a long-run growth anchor for that
          ZIP — the user still gets a forecast, it just isn't anchored to the global model.
        </p>
        <div className={styles.metricBlock}>
          {Object.entries(coverage.by_home_type).map(([ht, n]) => (
            <div key={ht} className={styles.coverageRow}>
              <span className={styles.coverageLabel}>{HOME_TYPE_LABEL[ht] ?? ht}</span>
              <span className={styles.coverageValue}>{fmtInt(n)} ZIPs</span>
            </div>
          ))}
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>
              <strong>Total predictions</strong>
            </span>
            <span className={styles.coverageValue}><strong>{fmtInt(coverage.total_predictions)}</strong></span>
          </div>
          {coverage.latest_price_month && (
            <div className={styles.coverageRow}>
              <span className={styles.coverageLabel}>Latest price month in DB</span>
              <span className={styles.coverageValue}>{fmtMonth(coverage.latest_price_month)}</span>
            </div>
          )}
        </div>
      </section>

      {/* ── Refresh cadence ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Refresh cadence</h2>
        <p>
          Every data source and every model is refreshed on the same cadence its source publishes —
          managed by Celery Beat (UTC times in <code>backend/tasks/celery_app.py</code>).
        </p>
        <div className={styles.metricBlock}>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>Mortgage rates (Freddie Mac PMMS)</span>
            <span className={styles.coverageValue}>Weekly · Friday 09:00</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>FRED macro series</span>
            <span className={styles.coverageValue}>Weekly · Monday 02:00</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>Zillow ZHVI (all 3 home types)</span>
            <span className={styles.coverageValue}>Monthly · 15th 03:00</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>Zillow metro supply &amp; rent</span>
            <span className={styles.coverageValue}>Monthly · 15th 03:30</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>BEA state GDP</span>
            <span className={styles.coverageValue}>Quarterly</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>LightGBM panel retrain</span>
            <span className={styles.coverageValue}>Monthly · 16th 02:00</span>
          </div>
          <div className={styles.coverageRow}>
            <span className={styles.coverageLabel}>Cached Prophet refresh</span>
            <span className={styles.coverageValue}>Monthly · 16th 04:00</span>
          </div>
        </div>
      </section>

      {/* ── Honest limitations ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Honest limitations</h2>
        <ul className={styles.list}>
          <li>
            <strong>12 months is the horizon. Period.</strong> The pipeline is tuned and
            backtested at the 12-month horizon. We could emit 24- or 36-month numbers — but the
            confidence intervals start losing calibration sharply, so we don't.
          </li>
          <li>
            <strong>Rate surprises are out of scope.</strong> The model sees the rate regime
            you're in via lagged mortgage-rate features, but a Fed pivot or a sudden cut isn't in
            any training row. The rate-scenario overlay on the forecast page lets you stress-test
            ±1 point.
          </li>
          <li>
            <strong>Local shocks are out of scope.</strong> A major employer leaving a metro, a
            wildfire, a rezoning vote, a corruption scandal — none of these are features. The
            model captures the general regime, not local one-offs.
          </li>
          <li>
            <strong>Coverage is uneven.</strong> Condo series are published in ~7.8k ZIPs;
            single-family in ~19.7k; the combined "all" index in ~26k. Tiny ZIPs may fall back to
            a long-run anchor rather than the global model.
          </li>
          <li>
            <strong>The 80% band's coverage isn't conformally calibrated.</strong> It's Prophet's
            band recentered on the blended endpoint. Adding empirical-coverage calibration is on
            the roadmap.
          </li>
          <li>
            <strong>No causal claims.</strong> The features predict; they don't explain. "Inventory
            up → prices down" is a statistical association in the training data, not a guarantee of
            causation in your ZIP next month.
          </li>
        </ul>
      </section>

      {/* ── Versioning ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Model versioning</h2>
        <p>
          Every training run gets a version string (currently{' '}
          <code>{model?.version ?? 'lgbm_panel_v4_typed'}</code>) and persists a row in{' '}
          <code>model_runs</code>. Cached forecasts are stamped with the version that produced
          them and re-trained on demand whenever the version changes or the cache is older than
          30 days. You always see numbers from the current model — never from a deprecated one.
        </p>
      </section>

      <p className={styles.note}>
        Source: <code>backend/app/ml/train_lgbm.py</code> · <code>backend/app/services/zip_projection.py</code> ·{' '}
        <code>backend/tasks/ml_tasks.py</code>
      </p>
    </div>
  )
}
