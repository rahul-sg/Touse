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
      <div className={styles.hero}>
        <div className={styles.heroCard}>
          <h1 className={styles.heroHeadline}>Find out what home you can afford.</h1>
          <p className={styles.heroSub}>Your income. Your savings. Your market.</p>
          <AffordabilityForm onSubmit={(data) => mutate(data)} isLoading={isPending} />
        </div>
      </div>

      <div className={styles.resultWrap}>
        <div className={styles.resultSection}>
          {isPending && (
            <div className={styles.placeholder}>
              <div className={styles.spinner} />
              <p>Calculating your range…</p>
            </div>
          )}

          {isError && (
            <div className={styles.errorBox}>
              Something went wrong. Check that the backend is running and try again.
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
              <p>Your results will appear here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
