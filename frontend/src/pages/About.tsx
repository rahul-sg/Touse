import styles from './About.module.css'

const SOURCES = [
  { name: 'Zillow Research', detail: 'Monthly median home values by ZIP code', url: 'https://www.zillow.com/research/data/' },
  { name: 'Freddie Mac PMMS', detail: 'Weekly 30- and 15-year fixed mortgage rates', url: 'https://www.freddiemac.com/pmms' },
  { name: 'FRED (St. Louis Fed)', detail: 'CPI, housing starts, Fed funds rate, unemployment', url: 'https://fred.stlouisfed.org/' },
  { name: 'BLS', detail: 'Metro-level unemployment', url: 'https://www.bls.gov/developers/' },
  { name: 'BEA', detail: 'State GDP growth', url: 'https://apps.bea.gov/API/' },
  { name: 'Census ACS', detail: 'Population and income by ZIP code', url: 'https://www.census.gov/data/developers/' },
  { name: 'HUD', detail: 'Fair market rents and housing policy', url: 'https://www.huduser.gov/portal/datasets/' },
  { name: 'MIT Election Lab', detail: 'State ballot outcomes and election results', url: 'https://electionlab.mit.edu/' },
  { name: 'Congress.gov', detail: 'Federal housing legislation', url: 'https://api.congress.gov/' },
]

export default function About() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>About Touse</h1>
      <p className={styles.lead}>
        Touse helps you understand what you can afford, where you can afford it, and where the
        market is heading — by combining personal finance calculations with real economic and
        political signals.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How affordability is calculated</h2>
        <p>
          We apply the standard <strong>28/36 rule</strong>: your monthly housing payment
          should not exceed 28% of gross monthly income, and total debt payments should not
          exceed 36%. Your credit score adjusts the mortgage rate estimate (based on typical
          lender tier premiums). The live 30-year fixed rate is pulled weekly from Freddie
          Mac's Primary Mortgage Market Survey so the calculation reflects current market conditions.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How the forecast works</h2>
        <p>
          Price forecasts use a three-tier approach that ships incrementally:
        </p>
        <ol className={styles.list}>
          <li><strong>Trend indicators</strong> — rolling 3-month and 12-month % change from Zillow median price history. No model required.</li>
          <li><strong>Prophet time series</strong> — Facebook Prophet trained per metro on historical Zillow data. Produces a 12-month forecast with an 80% confidence interval. Retrained monthly.</li>
          <li><strong>LightGBM with macro + political features</strong> — mortgage rate, CPI, unemployment, state GDP growth, Fed rate changes, zoning reform scores, first-time buyer credits, housing bond measures, and election year signals. (Coming soon.)</li>
        </ol>
        <p>
          Forecasts are shown as <strong>confidence ranges</strong>, not point predictions.
          Housing markets are noisy — an honest range is more useful than a false precision number.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Political and economic signals</h2>
        <p>
          We use <strong>quantified policy outcomes</strong>, not raw polling or sentiment.
          That means binary flags (is a first-time buyer credit active in this state?) and
          ordinal scores (how significant was the zoning reform?) rather than trying to model
          election outcomes directly. Sources are updated annually after each election cycle
          and federal budget cycle.
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
          <li>Listing data is cached and may be up to 6 hours stale.</li>
          <li>Policy flags are manually curated and updated annually — they may lag recent legislation.</li>
          <li>Listing map pins are approximate — when a listing has no precise coordinates we place it near the ZIP center.</li>
          <li>We model conventional, FHA, VA, USDA, ARM 5/1, and jumbo loans, but eligibility rules (e.g. VA service requirements, USDA rural limits) are not verified — confirm with a lender.</li>
        </ul>
      </section>
    </div>
  )
}
