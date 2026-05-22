import { Link } from 'react-router-dom'
import type { Scenario } from '../types'
import styles from './ScenarioCard.module.css'

interface Props {
  scenario: Scenario
  isActive: boolean
  isPrimary: boolean
  onSelect: () => void
  onDelete: () => void
  onSetPrimary: () => void
}

const LOAN_LABEL: Record<string, string> = {
  conventional: 'Conventional',
  fha: 'FHA',
  va: 'VA',
  usda: 'USDA',
  arm_5_1: 'ARM 5/1',
  jumbo: 'Jumbo',
}

function fmtPrice(n: number, type: 'buy' | 'rent'): string {
  if (type === 'rent') {
    return `$${n.toLocaleString()}/mo`
  }
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`
  return `$${n}`
}

export default function ScenarioCard({
  scenario,
  isActive,
  isPrimary,
  onSelect,
  onDelete,
  onSetPrimary,
}: Props) {
  return (
    <div
      className={`${styles.card} ${isActive ? styles.active : ''} ${isPrimary ? styles.primary : ''}`}
      onClick={onSelect}
    >
      <div className={styles.header}>
        <button
          className={`${styles.starBtn} ${isPrimary ? styles.starBtnActive : ''}`}
          onClick={e => { e.stopPropagation(); if (!isPrimary) onSetPrimary() }}
          title={isPrimary ? 'This is your primary scenario' : 'Set as primary scenario'}
          aria-label={isPrimary ? 'Primary scenario' : 'Set as primary scenario'}
        >
          {isPrimary ? '★' : '☆'}
        </button>
        <span className={styles.name}>{scenario.name}</span>
        <div className={styles.badges}>
          <span className={`${styles.badge} ${scenario.scenario_type === 'rent' ? styles.badgeRent : styles.badgeBuy}`}>
            {scenario.scenario_type.toUpperCase()}
          </span>
          {scenario.scenario_type === 'buy' && scenario.loan_type && scenario.loan_type !== 'conventional' && (
            <span className={styles.badgeLoan}>
              {LOAN_LABEL[scenario.loan_type] ?? scenario.loan_type.toUpperCase()}
            </span>
          )}
        </div>
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
          to={`/scenarios/${scenario.public_id}`}
          className={styles.viewBtn}
          onClick={e => e.stopPropagation()}
        >
          View details →
        </Link>
        <Link
          to="/map"
          state={{
            maxPrice: scenario.cached_max_price,
            scenarioName: scenario.name,
            targetZip: scenario.zip_code ?? undefined,
          }}
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
