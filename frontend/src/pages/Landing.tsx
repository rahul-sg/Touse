import { Link } from 'react-router-dom'
import styles from './Landing.module.css'

const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Create your free account',
    desc: 'Sign up in under a minute. No credit card, no credit pull — just your name and email to get started.',
  },
  {
    step: '02',
    title: 'Build your scenarios',
    desc: 'Enter your income, savings, and debt for any situation you want to explore. Buy now? Save more first? Rent instead? Model them all.',
  },
  {
    step: '03',
    title: 'See your homes and your score',
    desc: 'Browse real listings filtered to your budget on an interactive map. Get a readiness score and a clear action plan to improve it.',
  },
]

const FEATURES = [
  {
    icon: '✓',
    title: 'Your real number',
    desc: "We factor your income, debt load, credit score, and current mortgage rates to show your true max — not a bank's optimistic ceiling.",
  },
  {
    icon: '▲',
    title: 'Live market data',
    desc: 'Zillow price history, FRED macro signals, and our ML forecast tell you where prices are heading over the next 12 months.',
  },
  {
    icon: '⌂',
    title: 'Homes in your range',
    desc: "See exactly which listings you can afford on a map. Grayed-out homes above your budget show what you'd need to get there.",
  },
  {
    icon: '≡',
    title: 'Side-by-side scenarios',
    desc: 'Save multiple financial situations — "buy now", "save 6 more months", "combined income" — and compare them instantly.',
  },
  {
    icon: '◎',
    title: 'Readiness score',
    desc: 'A 0–100 score built from your DTI ratio, down payment, credit tier, and savings cushion, with a concrete action plan to improve it.',
  },
  {
    icon: '⌁',
    title: 'Buy or rent analysis',
    desc: 'Not sure if renting makes more sense right now? Model the rental side too and see your max affordable rent alongside move-in cost estimates.',
  },
]

const DATA_SOURCES = [
  { name: 'Zillow Research', desc: 'Monthly median home prices by metro' },
  { name: 'FRED (Federal Reserve)', desc: 'Mortgage rates, CPI, housing starts' },
  { name: 'BLS', desc: 'Employment data by metro area' },
  { name: 'Census ACS', desc: 'Population and income by ZIP code' },
  { name: 'BEA', desc: 'State-level GDP growth' },
  { name: 'HUD', desc: 'Fair market rents and policy data' },
]

const SCENARIOS = [
  {
    name: 'Buy now',
    income: '$95,000',
    savings: '$80,000',
    dp: '$50,000',
    max: '$420,000',
    score: 71,
    scoreLabel: 'Solid',
  },
  {
    name: 'Save 12 more months',
    income: '$95,000',
    savings: '$110,000',
    dp: '$70,000',
    max: '$510,000',
    score: 84,
    scoreLabel: 'Strong',
  },
  {
    name: 'With partner',
    income: '$155,000',
    savings: '$110,000',
    dp: '$70,000',
    max: '$740,000',
    score: 91,
    scoreLabel: 'Excellent',
  },
]

export default function Landing() {
  return (
    <div className={styles.page}>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <p className={styles.heroBadge}>Free · No credit pull · No bank required</p>
          <h1 className={styles.heroHeadline}>Know exactly what home you can afford.</h1>
          <p className={styles.heroSub}>
            Touse combines your financial picture with live market data and our forecasting model to
            show you homes in your real budget — not just what the bank says.
          </p>
          <div className={styles.heroActions}>
            <Link to="/onboarding" className={styles.ctaBtn}>
              Get started free →
            </Link>
            <Link to="/login" className={styles.ghostBtn}>
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className={styles.howSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionEyebrow}>How it works</p>
          <h2 className={styles.sectionHeadline}>From signup to your homes in minutes.</h2>
          <div className={styles.howGrid}>
            {HOW_IT_WORKS.map((step) => (
              <div key={step.step} className={styles.howCard}>
                <span className={styles.howStep}>{step.step}</span>
                <h3 className={styles.howTitle}>{step.title}</h3>
                <p className={styles.howDesc}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className={styles.featuresSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionEyebrow}>What you get</p>
          <h2 className={styles.sectionHeadline}>Everything in one place.</h2>
          <div className={styles.featuresGrid}>
            {FEATURES.map((f) => (
              <div key={f.title} className={styles.featureCard}>
                <span className={styles.featureIcon}>{f.icon}</span>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Scenario comparison ── */}
      <section className={styles.scenarioSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionEyebrow}>Saved scenarios</p>
          <h2 className={styles.sectionHeadline}>Model every situation. Pick the right move.</h2>
          <p className={styles.scenarioIntro}>
            Most people only ever run one number. Touse lets you save and name as many scenarios as you
            want — so you can see exactly how six more months of saving, a second income, or a different
            ZIP code changes your picture.
          </p>
          <div className={styles.scenarioCards}>
            {SCENARIOS.map((s) => (
              <div key={s.name} className={styles.scenarioCard}>
                <div className={styles.scenarioCardTop}>
                  <span className={styles.scenarioName}>{s.name}</span>
                  <span
                    className={styles.scenarioScore}
                    style={{ '--score': s.score } as React.CSSProperties}
                  >
                    {s.score}
                  </span>
                </div>
                <div className={styles.scenarioRow}>
                  <span className={styles.scenarioLabel}>Income</span>
                  <span className={styles.scenarioVal}>{s.income}</span>
                </div>
                <div className={styles.scenarioRow}>
                  <span className={styles.scenarioLabel}>Savings</span>
                  <span className={styles.scenarioVal}>{s.savings}</span>
                </div>
                <div className={styles.scenarioRow}>
                  <span className={styles.scenarioLabel}>Down payment</span>
                  <span className={styles.scenarioVal}>{s.dp}</span>
                </div>
                <div className={styles.scenarioDivider} />
                <div className={styles.scenarioMax}>
                  <span className={styles.scenarioMaxLabel}>Max home price</span>
                  <span className={styles.scenarioMaxVal}>{s.max}</span>
                </div>
                <span className={styles.scenarioScoreLabel}>{s.scoreLabel} readiness</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ML Forecast ── */}
      <section className={styles.forecastSection}>
        <div className={styles.forecastInner}>
          <div className={styles.forecastText}>
            <p className={styles.sectionEyebrow}>Market intelligence</p>
            <h2 className={styles.forecastHeadline}>A forecast, not just a calculator.</h2>
            <p className={styles.forecastDesc}>
              Most tools tell you what you can borrow today. Touse goes further. Our machine learning
              model is trained on years of Zillow price history, FRED economic indicators, Zillow
              supply signals (active listings, days on market, price cuts), and local market data to
              project where prices in your target area are heading over the next 12 months.
            </p>
            <p className={styles.forecastDesc}>
              That means you can see whether now is a smart time to buy, or whether waiting six months
              might save you tens of thousands. Your budget, your timeline, your call.
            </p>
            <Link to="/onboarding" className={styles.forecastCta}>
              See your forecast →
            </Link>
          </div>
          <div className={styles.forecastVisual}>
            <div className={styles.fvChart}>
              <div className={styles.fvBar} style={{ '--h': '55%' } as React.CSSProperties} />
              <div className={styles.fvBar} style={{ '--h': '60%' } as React.CSSProperties} />
              <div className={styles.fvBar} style={{ '--h': '58%' } as React.CSSProperties} />
              <div className={styles.fvBar} style={{ '--h': '65%' } as React.CSSProperties} />
              <div className={styles.fvBar} style={{ '--h': '70%' } as React.CSSProperties} />
              <div className={styles.fvBar} style={{ '--h': '68%' } as React.CSSProperties} />
              <div className={styles.fvBarForecast} style={{ '--h': '74%' } as React.CSSProperties} />
              <div className={styles.fvBarForecast} style={{ '--h': '78%' } as React.CSSProperties} />
              <div className={styles.fvBarForecast} style={{ '--h': '76%' } as React.CSSProperties} />
            </div>
            <p className={styles.fvLabel}>12-month price forecast · Austin, TX</p>
          </div>
        </div>
      </section>

      {/* ── Data sources ── */}
      <section className={styles.dataSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionEyebrow}>Data sources</p>
          <h2 className={styles.sectionHeadline}>Built on real data, not estimates.</h2>
          <p className={styles.dataIntro}>
            Every number Touse shows you is derived from authoritative public data sources — the same
            ones economists and housing researchers use.
          </p>
          <div className={styles.dataGrid}>
            {DATA_SOURCES.map((d) => (
              <div key={d.name} className={styles.dataCard}>
                <span className={styles.dataName}>{d.name}</span>
                <span className={styles.dataDesc}>{d.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className={styles.ctaSection}>
        <div className={styles.ctaInner}>
          <h2 className={styles.ctaHeadline}>Ready to know your real number?</h2>
          <p className={styles.ctaSub}>
            Free forever. No credit pull. No mortgage broker pitch. Just your real budget and the
            homes that fit it.
          </p>
          <Link to="/onboarding" className={styles.ctaBtn}>
            Create your free account →
          </Link>
        </div>
      </section>

      <footer className={styles.footer}>
        &copy; {new Date().getFullYear()} Touse. All rights reserved.
      </footer>
    </div>
  )
}
