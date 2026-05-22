import ContactForm from '../components/ContactForm'
import styles from './About.module.css'

const SOURCES = [
  { name: 'Zillow Research', detail: 'Monthly median home values by ZIP code', url: 'https://www.zillow.com/research/data/' },
  { name: 'Freddie Mac PMMS', detail: 'Weekly 30- and 15-year fixed mortgage rates', url: 'https://www.freddiemac.com/pmms' },
  { name: 'FRED (St. Louis Fed)', detail: 'CPI, housing starts, Fed funds rate, unemployment', url: 'https://fred.stlouisfed.org/' },
  { name: 'BEA', detail: 'State-level GDP growth', url: 'https://apps.bea.gov/API/' },
  { name: 'US Census Bureau', detail: 'ZIP boundaries and address geocoding', url: 'https://geocoding.geo.census.gov/' },
]

export default function About() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>About Touse</h1>
      <p className={styles.lead}>
        Touse helps you understand what you can afford, where you can afford it, and where the
        market is heading — by combining personal-finance math with live housing and economic data.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How affordability is calculated</h2>
        <p>
          We apply the standard <strong>28/36 rule</strong>: your monthly housing payment
          should not exceed 28% of gross monthly income, and total debt payments should not
          exceed 36%. Your credit score adjusts the mortgage rate estimate (based on typical
          lender tier premiums). The live 30-year fixed rate is pulled weekly from Freddie
          Mac's Primary Mortgage Market Survey so the calculation reflects current market conditions.
          We model conventional, FHA, VA, USDA, ARM 5/1, and jumbo loans, each with its own
          down-payment and DTI rules.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How the forecast works</h2>
        <p>
          Each ZIP code's 12-month price forecast comes from a <strong>Prophet</strong> time-series
          model trained on that ZIP's full Zillow price history. To stop a recent boom from
          extrapolating at full slope for an entire year, the projection is blended toward the
          area's long-run growth rate — trusting the model near-term and the historical norm
          further out. Forecasts are shown as <strong>confidence ranges</strong>, not point
          predictions: housing is noisy, and an honest range beats false precision.
        </p>
        <p>
          Because the model is trained on price history alone, it cannot anticipate interest-rate
          moves — the single biggest swing factor for housing. Rather than pretend otherwise, the
          forecast page lets you overlay <strong>rate scenarios</strong> (rates ±1 point) so you
          can see that sensitivity directly.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Market context</h2>
        <p>
          Alongside each forecast we show the broader conditions that move housing: the current
          30-year mortgage rate, year-over-year inflation (CPI), national unemployment, and your
          state's GDP growth. These come straight from Freddie Mac, FRED, and the BEA — and are
          refreshed automatically on a schedule, so what you see reflects the latest releases.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Data sources</h2>
        <div className={styles.sourceGrid}>
          {SOURCES.map((s) => (
            <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer" className={styles.sourceCard}>
              <strong className={styles.sourceName}>{s.name}</strong>
              <span className={styles.sourceDetail}>{s.detail}</span>
            </a>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Limitations</h2>
        <ul className={styles.list}>
          <li>Forecasts beyond 12 months are unreliable — we don't show them.</li>
          <li>The forecast model is trend-based; it does not predict interest rates or economic shocks.</li>
          <li>Listing data is cached and may be up to 6 hours stale.</li>
          <li>Listing map pins are approximate — when an address can't be geocoded precisely we place it near the ZIP center.</li>
          <li>Loan eligibility rules (e.g. VA service requirements, USDA rural limits) are not verified — always confirm with a lender.</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>About the creators</h2>
        <p>
          Touse is an independent project built to make home affordability transparent — bringing
          personal-finance math, live market data, and price forecasting into one place instead of
          a dozen browser tabs. It's actively being developed, and feedback genuinely shapes what
          gets built next.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Get in touch</h2>
        <p>
          Questions, bugs, or ideas? Send us a note — it goes straight to the team.
        </p>
        <ContactForm />
      </section>
    </div>
  )
}
