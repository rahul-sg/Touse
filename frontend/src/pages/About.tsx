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
          Each ZIP code's 12-month price forecast is a two-stage pipeline. A
          global <strong>LightGBM panel model</strong> trained on every ZIP × month
          in Zillow's history — with lagged prices and growth rates, US macro
          (mortgage rate, CPI, fed funds, unemployment, housing starts, consumer
          sentiment), metro-level supply and rent signals from Zillow Research,
          and an election-cycle flag — produces a 12-month growth-rate anchor.
          A per-ZIP <strong>Prophet</strong> time-series model then shapes the
          monthly trajectory and confidence band toward that anchor, so the
          near-term path respects local seasonality while the endpoint reflects
          national and metro conditions.
        </p>
        <p>
          Forecasts are <strong>type-aware</strong>: you can switch between an
          all-homes index, single-family only, or condos only. Zillow publishes
          separate ZHVI series for each, and condos and single-family homes
          often grow at meaningfully different rates in the same ZIP — the
          model treats the home type as a categorical feature so it can learn
          those differences.
        </p>
        <p>
          Forecasts are shown as <strong>confidence ranges</strong>, not point
          predictions: housing is noisy, and an honest range beats false
          precision. Even with macro features, the model can't anticipate
          policy shocks or rate surprises, so the forecast page also lets you
          overlay <strong>rate scenarios</strong> (rates ±1 point) to see that
          sensitivity directly.
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
          <li>The forecast model uses macro features but cannot predict interest-rate surprises or policy shocks — use the rate-scenario overlay to stress-test sensitivity.</li>
          <li>Condo and single-family forecasts are only available in ZIPs where Zillow publishes a separate series for that type; elsewhere, switch to "All homes" to see a forecast.</li>
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
