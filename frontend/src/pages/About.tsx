import { Link } from 'react-router-dom'
import ContactForm from '../components/ContactForm'
import styles from './About.module.css'

const SOURCES = [
  { name: 'Zillow Research', detail: 'Monthly Home Value Index (ZHVI) by ZIP × home type (all / SFR / condo); metro-level supply and rent panel', url: 'https://www.zillow.com/research/data/' },
  { name: 'Freddie Mac PMMS', detail: 'Weekly 30- and 15-year fixed mortgage rates — the live rate that drives every affordability calculation', url: 'https://www.freddiemac.com/pmms' },
  { name: 'FRED (St. Louis Fed)', detail: 'CPI, fed funds rate, unemployment, housing starts, UMich consumer sentiment, new-home sales', url: 'https://fred.stlouisfed.org/' },
  { name: 'BEA', detail: 'State-level GDP growth, refreshed quarterly', url: 'https://apps.bea.gov/API/' },
  { name: 'US Census Bureau', detail: 'ZIP centroids and address geocoding for the listings map', url: 'https://geocoding.geo.census.gov/' },
  { name: 'RapidAPI realty-us', detail: 'Live for-sale listings (cached for 6 hours)', url: 'https://rapidapi.com/' },
]

const LOAN_RULES = [
  { name: 'Conventional', dp: '5–20%', limit: '$766,550 (conforming)', notes: 'PMI required under 20% down; falls off at 20% equity.' },
  { name: 'FHA', dp: '3.5%', limit: 'Varies by county', notes: '1.75% upfront MIP (financed) + annual MIP. Easier credit requirements.' },
  { name: 'VA', dp: '0%', limit: 'No cap with full entitlement', notes: 'No PMI. Funding fee varies by service category — not modeled in our estimate.' },
  { name: 'USDA', dp: '0%', limit: 'Income-capped, rural areas only', notes: 'Eligibility is location and income dependent — we don\'t verify either.' },
  { name: 'ARM 5/1', dp: '5–20%', limit: 'Same as conventional', notes: 'Fixed for 5 years, then adjusts annually. We use the introductory rate.' },
  { name: 'Jumbo', dp: '10–20%', limit: 'Above conforming', notes: 'Used automatically when your purchase price exceeds the conforming limit.' },
]

export default function About() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>About Touse</h1>
      <p className={styles.lead}>
        Touse helps you understand <strong>what you can afford</strong>, <strong>where you can afford
        it</strong>, and <strong>where the market is heading</strong> — by combining personal-finance
        math with live housing and economic data. Every number you see is computed from the same
        public datasets the Federal Reserve and major real-estate sites use, refreshed automatically.
      </p>

      {/* ── What it does ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What Touse does, end to end</h2>
        <p>
          A typical session goes like this: you enter your income, savings, debt, and credit tier;
          we compute your real maximum home price across six loan programs at today's live mortgage
          rate; you save that as a <em>scenario</em> (and a few alternatives — "save 6 more months",
          "with partner") and pick the primary one; the map shows actual for-sale listings filtered
          to your budget, geocoded to their real coordinates; and the forecast page shows where
          prices in your target ZIP are heading over the next 12 months — broken down by home type,
          with a rate-scenario overlay so you can stress-test the answer.
        </p>
        <p>
          Behind the scenes a <em>readiness score</em> from 0 to 100 — built from your projected
          debt-to-income ratio (including the new mortgage), down-payment size, credit tier, and
          savings cushion — turns the inputs into a single number with a concrete action plan to
          improve it.
        </p>
      </section>

      {/* ── Affordability ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How affordability is calculated</h2>
        <p>
          We apply the standard <strong>28/36 rule</strong>: your monthly housing payment should not
          exceed 28% of gross monthly income, and total debt payments (housing + car + student +
          credit cards + other) should not exceed 36%. The smaller of those two ceilings becomes
          your maximum monthly housing payment, which is then converted into a maximum loan amount
          using the standard amortization formula:
        </p>
        <pre className={styles.codeBlock}>
P = L · r / (1 − (1 + r)<sup>−n</sup>)
        </pre>
        <p>
          where <em>P</em> is the monthly payment, <em>L</em> is the loan principal, <em>r</em> is
          the monthly interest rate (annual ÷ 12), and <em>n</em> is the number of monthly payments
          (term in years × 12). We solve for <em>L</em> given your maximum affordable <em>P</em>,
          then add your down payment to get your maximum purchase price.
        </p>
        <p>
          Your credit score adjusts the mortgage rate estimate using typical lender-tier premiums
          (≈0pp at 760+, +0.3pp at 720–759, +0.8pp at 670–719, escalating below). The base 30-year
          fixed rate is pulled weekly from <strong>Freddie Mac's Primary Mortgage Market Survey</strong>{' '}
          (PMMS), so the calculation reflects current market conditions — not a stale snapshot.
        </p>
        <h3 className={styles.subSectionTitle}>Loan programs we model</h3>
        <div className={styles.tableWrap}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Loan</th>
                <th>Min down</th>
                <th>Limit</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {LOAN_RULES.map(l => (
                <tr key={l.name}>
                  <td><strong>{l.name}</strong></td>
                  <td>{l.dp}</td>
                  <td>{l.limit}</td>
                  <td>{l.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={styles.note}>
          PMI on conventional loans is estimated at typical industry rates (0.55–1.0% annualized
          depending on credit tier and down-payment size) and drops off when you reach 20% equity.
          We don't model property taxes or homeowners insurance in the monthly payment — both vary
          enormously by ZIP and assessment — so add ~$200–$600/mo to the displayed payment for a
          realistic all-in figure.
        </p>
      </section>

      {/* ── Readiness ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How the readiness score works</h2>
        <p>
          The readiness score blends five forward-looking dimensions into a single 0–100 number for
          <strong> buy</strong> scenarios (four for rent scenarios). The dimensions are designed to
          capture what actually goes wrong for first-time buyers in the year after closing — not
          just whether you qualify on paper.
        </p>
        <ul className={styles.list}>
          <li>
            <strong>Projected DTI</strong> (35% weight) — your debt-to-income ratio <em>including</em>{' '}
            the new mortgage payment you'd be taking on, not the optimistic version that excludes it.
          </li>
          <li>
            <strong>Down payment</strong> (20%) — scored against the 20% threshold where you avoid
            PMI; smaller down payments aren't disqualifying but cost more long-term.
          </li>
          <li>
            <strong>Credit tier</strong> (20%) — banded the way mortgage lenders actually price risk
            (760+, 720–759, 670–719, 620–669, below).
          </li>
          <li>
            <strong>Cushion</strong> (15%) — months of total housing payment your liquid savings
            cover after the down payment. Three months is shaky; six is comfortable.
          </li>
          <li>
            <strong>Market fit</strong> (10%) — does your max price overlap with current median
            home values in your target ZIP? A perfect financial profile in a market you've priced
            yourself out of isn't actually ready.
          </li>
        </ul>
      </section>

      {/* ── Forecast ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How the forecast works</h2>
        <p>
          Each ZIP code's 12-month price forecast is a <strong>two-stage pipeline</strong>. We chose
          this design because the two failure modes of a price forecast are different problems that
          benefit from different tools.
        </p>
        <p>
          <strong>Stage 1 — the endpoint.</strong> A global <strong>LightGBM panel model</strong>{' '}
          trained on every ZIP × home-type × month in Zillow's history — features include lagged
          prices and growth rates (1, 3, 6, 12, 24 months), US macro signals (mortgage rate plus
          its lags and recent change, CPI year-over-year, fed funds and its 3-/12-month change,
          unemployment, housing starts, UMich consumer sentiment, new-home sales), metro-level
          supply and rent dynamics from Zillow Research (for-sale inventory, new listings, days on
          market, % price-cut, median rent, rent-to-price ratio), an election-year flag, and
          cyclical month encodings. The model emits a single 12-month price-growth percentage
          per (ZIP, home type).
        </p>
        <p>
          <strong>Stage 2 — the path.</strong> A per-(ZIP, home_type) <strong>Prophet</strong>{' '}
          time-series model is fit on demand the first time you ask for a forecast there. Prophet
          handles the local seasonality and produces an 80% confidence band; its 12-month endpoint
          is then blended toward the LightGBM anchor (heavy weight on the anchor at month 12,
          lighter weight near term where the local time-series signal is strongest). The cached
          result is served instantly on subsequent requests.
        </p>
        <p>
          Forecasts are <strong>type-aware</strong>: switch between all-homes, single-family only,
          or condo only. Zillow publishes separate ZHVI series for each, and condos and
          single-family homes frequently grow at different rates in the same ZIP — the model treats
          home type as a categorical feature so it can learn those differences.
        </p>
        <Link to="/methodology" className={styles.deepDiveCard}>
          <div className={styles.deepDiveBody}>
            <p className={styles.deepDiveEyebrow}>Deep dive</p>
            <p className={styles.deepDiveTitle}>Read the full methodology →</p>
            <p className={styles.deepDiveDesc}>
              The live model card, backtest accuracy per home type, the math behind the
              anchoring + blend, every feature, refresh cadence, and honest limitations.
            </p>
          </div>
        </Link>
        <h3 className={styles.subSectionTitle}>Why a range and not a single number</h3>
        <p>
          Housing prices are noisy — random factors (one outlier sale, a rezoning vote, a major
          employer announcement) routinely move a ZIP's median by 1–3% in a single month. A point
          forecast hides that noise; a confidence band exposes it honestly. The shaded area on the
          forecast chart is an 80% interval: roughly four times out of five, the realized price
          should land inside it.
        </p>
        <h3 className={styles.subSectionTitle}>Rate scenario overlays</h3>
        <p>
          Even with macro features, the model can't anticipate a sudden rate move or a policy shock.
          The <em>Rates ±1 point</em> overlay on the forecast chart applies an illustrative price
          elasticity (about 4% per 1-point rate move, ramping linearly across the 12-month horizon)
          to show how sensitive your ZIP would be. This is intentionally simple — the goal is to
          give you a visceral sense of rate risk, not to layer a second model on top.
        </p>
      </section>

      {/* ── Market context ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Market context</h2>
        <p>
          Alongside each forecast we show the broader conditions that move housing: the current
          30-year mortgage rate (Freddie Mac), year-over-year inflation (CPI from FRED), national
          unemployment (FRED), and your state's GDP growth (BEA). These come straight from the
          source and are refreshed automatically — Freddie Mac mortgage rates weekly, FRED series
          weekly, BEA state GDP quarterly — so what you see reflects the latest release.
        </p>
      </section>

      {/* ── Listings ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How the listings map works</h2>
        <p>
          We pull live for-sale listings from a RapidAPI realty endpoint when you query an area,
          then geocode each address to real coordinates via the <strong>US Census geocoder</strong>{' '}
          (free, no API key). Successfully geocoded addresses land at their real lat/lng;
          addresses the geocoder can't match (≈25% in practice) fall back to the ZIP centroid so
          they still appear on the map. The full snapshot is cached for 6 hours to keep the
          experience snappy and the API usage reasonable.
        </p>
        <p>
          Listings can be filtered by max price (set automatically from your primary scenario),
          minimum beds and baths, property type, square footage, year built, and lot size.
          Clicking a card in the sidebar flies the map to the listing and opens its popup with
          a link to the original listing.
        </p>
      </section>

      {/* ── Refresh cadence ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How fresh is the data?</h2>
        <p>
          Every market data source is refreshed by a scheduled Celery job that runs on the same
          cadence the publisher itself releases data — so what you see is never more than one
          publication cycle behind.
        </p>
        <ul className={styles.list}>
          <li><strong>Mortgage rates</strong> — Freddie Mac PMMS, weekly (Fridays)</li>
          <li><strong>FRED macro series</strong> — weekly pass picks up monthly + back-revisions</li>
          <li><strong>Zillow ZHVI</strong> (3 home types) — monthly, mid-month</li>
          <li><strong>Zillow metro supply &amp; rent</strong> — monthly, mid-month</li>
          <li><strong>BEA state GDP</strong> — quarterly</li>
          <li><strong>LightGBM panel retraining</strong> — monthly, day after fresh Zillow data lands</li>
          <li><strong>Cached Prophet forecasts</strong> — refreshed after each LightGBM retrain</li>
          <li><strong>Live listings</strong> — 6-hour cache</li>
        </ul>
      </section>

      {/* ── Data sources ── */}
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

      {/* ── Privacy ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What we store, what we don't</h2>
        <p>
          Your account holds your name, email, optional username, hashed password (bcrypt), and the
          financial details you choose to save into scenarios. Scenarios are keyed by a
          non-enumerable opaque ID — even if someone guessed your URL pattern they couldn't list or
          read another user's scenarios. Every API endpoint that touches user data verifies
          ownership via a signed JWT.
        </p>
        <p>
          We don't pull a credit report, we don't share data with lenders, and we don't run paid
          ads against your profile. Touse has no relationship with the listings we surface beyond
          fetching them from a public-facing real-estate feed. Verification emails are sent through
          Resend; if Resend is unconfigured the email is logged and the account still works.
        </p>
        <p>
          You're in control of your account. Forgot your password? Request a reset link from the
          sign-in page and we'll email you a one-time link that expires in an hour. Done with
          Touse? The Profile page has a "Danger zone" that permanently deletes your account and
          every scenario you've saved — there's no soft-delete, no recovery, no "we kept a copy
          just in case." Type DELETE, confirm, and your data is gone.
        </p>
        <p>
          The app is built mobile-first: the navigation collapses to a drawer on phones, the map
          page shows a swipe-up bottom drawer for listings, and form inputs are sized to avoid
          iOS's annoying auto-zoom on focus. Use Touse from your laptop while doing your taxes,
          or pull it up on your phone while you're walking through an open house.
        </p>
      </section>

      {/* ── Limitations ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Limitations — read these</h2>
        <ul className={styles.list}>
          <li>
            <strong>Forecasts beyond 12 months are unreliable</strong> — we don't show them. The
            two-stage pipeline is tuned and backtested at the 12-month horizon and starts losing
            calibration quickly past that.
          </li>
          <li>
            <strong>The model can't predict rate or policy surprises.</strong> It uses macro
            features so it sees the regime you're in, but a Fed pivot or a sudden tax-credit
            program isn't in any training row. Use the rate-scenario overlay to stress-test.
          </li>
          <li>
            <strong>Condo and single-family forecasts</strong> are only available in ZIPs where
            Zillow publishes a separate series for that type; elsewhere, switch to "All homes."
            ZIPs with very thin condo or SFR history will gracefully fall back to a long-run growth
            anchor rather than an LGBM-anchored prediction.
          </li>
          <li>
            <strong>Property taxes and insurance are not in the monthly payment estimate.</strong>{' '}
            Add ~$200–$600/mo depending on state and assessment for the all-in figure.
          </li>
          <li>
            <strong>Listing data is cached and may be up to 6 hours stale;</strong> a small
            percentage of addresses fall back to the ZIP centroid when the geocoder can't match.
          </li>
          <li>
            <strong>Loan eligibility rules are not verified</strong> (VA service requirements, USDA
            rural / income limits, jumbo qualification thresholds) — always confirm with a lender.
          </li>
          <li>
            <strong>This is not financial advice.</strong> Touse is a planning tool. Talk to a
            licensed professional before making a major financial decision.
          </li>
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
