import { useNavigate } from 'react-router-dom'
import AffordabilityForm from './AffordabilityForm'
import AffordabilityResult from './AffordabilityResult'
import { useAffordability } from '../hooks/useAffordability'
import styles from './AffordabilityCalculator.module.css'

/**
 * Anonymous affordability calculator — embedded on the landing page so visitors
 * can try the core value before signing up.
 */
export default function AffordabilityCalculator() {
  const navigate = useNavigate()
  const { mutate, data, isPending, isError } = useAffordability()

  return (
    <div className={styles.wrap}>
      <div className={styles.formCard}>
        <AffordabilityForm onSubmit={(d) => mutate(d)} isLoading={isPending} />
      </div>

      <div className={styles.resultCard}>
        {isPending && (
          <div className={styles.placeholder}>
            <div className={styles.spinner} />
            <p>Calculating your range…</p>
          </div>
        )}

        {isError && (
          <div className={styles.errorBox}>
            Couldn't calculate your range right now. Please try again in a moment.
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
  )
}
