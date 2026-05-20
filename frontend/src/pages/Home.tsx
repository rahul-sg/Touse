import { useNavigate } from 'react-router-dom'
import AffordabilityForm from '../components/AffordabilityForm'
import AffordabilityResult from '../components/AffordabilityResult'
import { useAffordability } from '../hooks/useAffordability'
import styles from './Home.module.css'

export default function Home() {
  const navigate = useNavigate()
  const { mutate, data, isPending, isError } = useAffordability()

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.headline}>What can you afford?</h1>
        <p className={styles.sub}>
          Enter your finances and we'll show you your buying range, map affordable
          listings, and forecast where prices are heading.
        </p>
      </header>

      <div className={styles.content}>
        <section className={styles.formSection}>
          <h2 className={styles.sectionTitle}>Your finances</h2>
          <AffordabilityForm onSubmit={(data) => mutate(data)} isLoading={isPending} />
        </section>

        <section className={styles.resultSection}>
          {isPending && (
            <div className={styles.placeholder}>
              <div className={styles.spinner} />
              <p>Calculating…</p>
            </div>
          )}

          {isError && (
            <div className={styles.errorBox}>
              <p>Something went wrong. Check that the backend is running and try again.</p>
            </div>
          )}

          {data && !isPending && (
            <>
              <AffordabilityResult result={data} />
              <button
                className={styles.mapBtn}
                onClick={() => navigate('/map', { state: { maxPrice: data.max_price } })}
              >
                See homes in my range →
              </button>
            </>
          )}

          {!data && !isPending && !isError && (
            <div className={styles.placeholder}>
              <p>Fill in your finances to see your home buying range.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
