import { Link } from 'react-router-dom'
import type { Scenario } from '../types'
import styles from './ScenarioCard.module.css'

interface Props {
  scenario: Scenario
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}

function fmtPrice(n: number, type: 'buy' | 'rent'): string {
  if (type === 'rent') {
    return `$${n.toLocaleString()}/mo`
  }
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`
  return `$${n}`
}

export default function ScenarioCard({ scenario, isActive, onSelect, onDelete }: Props) {
  return (
    <div
      className={`${styles.card} ${isActive ? styles.active : ''}`}
      onClick={onSelect}
    >
      <div className={styles.header}>
        <span className={styles.name}>{scenario.name}</span>
        <span className={`${styles.badge} ${scenario.scenario_type === 'rent' ? styles.badgeRent : styles.badgeBuy}`}>
          {scenario.scenario_type.toUpperCase()}
        </span>
      </div>

      {scenario.cached_max_price != null ? (
        <p className={styles.price}>{fmtPrice(scenario.cached_max_price, scenario.scenario_type)}</p>
      ) : (
        <p className={styles.priceEmpty}>No result yet</p>
      )}

      {scenario.zip_code && (
        <p className={styles.location}>{scenario.zip_code}</p>
      )}

      <div className={styles.actions}>
        <Link
          to={`/scenarios/${scenario.id}`}
          className={styles.viewBtn}
          onClick={e => e.stopPropagation()}
        >
          View details →
        </Link>
        <Link
          to="/map"
          state={{ maxPrice: scenario.cached_max_price, scenarioId: scenario.id, scenarioName: scenario.name }}
          className={styles.mapBtn}
          onClick={e => e.stopPropagation()}
        >
          Map
        </Link>
        <button
          className={styles.deleteBtn}
          onClick={e => { e.stopPropagation(); onDelete() }}
          title="Delete scenario"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
