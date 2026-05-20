import { Link } from 'react-router-dom'
import styles from './Landing.module.css'

const FEATURES = [
  {
    icon: '✓',
    title: 'Your real number',
    desc: 'We factor your income, debt load, credit score, and current mortgage rates to show your true max.',
  },
  {
    icon: '▲',
    title: 'Live market data',
    desc: 'Zillow price history, FRED macro signals, and our ML forecast tell you where prices are heading.',
  },
  {
    icon: '⌂',
    title: 'Homes in your range',
    desc: 'See exactly which listings you can afford on a map, and what it takes to stretch to others.',
  },
]

export default function Landing() {
  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroHeadline}>Know exactly what home you can afford.</h1>
          <p className={styles.heroSub}>
            Touse combines your financial picture with live market data and our forecasting model to
            show you homes in your real budget not just what the bank says.
          </p>
          <Link to="/onboarding" className={styles.ctaBtn}>
            Get started free
          </Link>
        </div>
      </section>

      <section className={styles.features}>
        {FEATURES.map((f) => (
          <div key={f.title} className={styles.featureCard}>
            <span className={styles.featureIcon}>{f.icon}</span>
            <h3 className={styles.featureTitle}>{f.title}</h3>
            <p className={styles.featureDesc}>{f.desc}</p>
          </div>
        ))}
      </section>

      <section className={styles.forecastSection}>
        <div className={styles.forecastInner}>
          <div className={styles.forecastText}>
            <h2 className={styles.forecastHeadline}>A forecast, not just a calculator.</h2>
            <p className={styles.forecastDesc}>
              Most tools tell you what you can borrow today. Touse goes further. Our machine
              learning model is trained on years of Zillow price history, FRED economic indicators,
              and local market signals to project where prices in your target area are heading over
              the next 12 months.
            </p>
            <p className={styles.forecastDesc}>
              That means you can see whether now is a smart time to buy, or whether waiting six
              months might save you tens of thousands. Your budget, your timeline, your call.
            </p>
          </div>
          <div className={styles.forecastVisual}>
            <span className={styles.forecastVisualIcon}>&#128200;</span>
            <span>12-month price forecast</span>
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        &copy; {new Date().getFullYear()} Touse. All rights reserved.
      </footer>
    </div>
  )
}
