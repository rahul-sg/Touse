import { useEffect, useRef, useState } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import type { PropertyType } from '../types'
import styles from './MapFilterBar.module.css'

interface Props {
  maxPrice: number
  onMaxPriceChange: (v: number) => void
  minBeds: number
  onMinBedsChange: (v: number) => void
  propertyTypes: PropertyType[]
  onPropertyTypesChange: (v: PropertyType[]) => void
  minSqft?: number
  onMinSqftChange: (v: number | undefined) => void
  minYearBuilt?: number
  onMinYearBuiltChange: (v: number | undefined) => void
  resultCount: number
}

const PROPERTY_TYPE_OPTIONS: { value: PropertyType; label: string }[] = [
  { value: 'single_family', label: 'House' },
  { value: 'condo',         label: 'Condo' },
  { value: 'townhouse',     label: 'Townhouse' },
  { value: 'multi_family',  label: 'Multi-fam' },
  { value: 'mobile',        label: 'Mobile' },
  { value: 'land',          label: 'Land' },
]

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function MapFilterBar({
  maxPrice,
  onMaxPriceChange,
  minBeds,
  onMinBedsChange,
  propertyTypes,
  onPropertyTypesChange,
  minSqft,
  onMinSqftChange,
  minYearBuilt,
  onMinYearBuiltChange,
  resultCount,
}: Props) {
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const advancedRef = useRef<HTMLDivElement | null>(null)

  // Close the "More filters" popover on outside click.
  useEffect(() => {
    if (!advancedOpen) return
    function onClick(e: MouseEvent) {
      if (advancedRef.current && !advancedRef.current.contains(e.target as Node)) {
        setAdvancedOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [advancedOpen])

  function toggleType(t: PropertyType) {
    const next = propertyTypes.includes(t)
      ? propertyTypes.filter(x => x !== t)
      : [...propertyTypes, t]
    onPropertyTypesChange(next)
  }

  const activeAdvancedCount = (minSqft ? 1 : 0) + (minYearBuilt ? 1 : 0)

  return (
    <div className={styles.bar}>
      {/* Max price slider */}
      <div className={styles.group}>
        <span className={styles.label}>Max price</span>
        <div className={styles.priceControl}>
          <input
            type="range"
            min={100_000}
            max={3_000_000}
            step={10_000}
            value={maxPrice}
            onChange={(e) => onMaxPriceChange(Number(e.target.value))}
            className={styles.range}
            aria-label="Max price"
          />
          <span className={styles.priceValue}>{fmt(maxPrice)}</span>
        </div>
      </div>

      <div className={styles.divider} aria-hidden="true" />

      {/* Min beds */}
      <div className={styles.group}>
        <span className={styles.label}>Beds</span>
        <div className={styles.chipGroup}>
          {[1, 2, 3, 4].map((n) => (
            <button
              key={n}
              type="button"
              className={`${styles.chip} ${minBeds === n ? styles.chipActive : ''}`}
              onClick={() => onMinBedsChange(n)}
            >
              {n}+
            </button>
          ))}
        </div>
      </div>

      <div className={styles.divider} aria-hidden="true" />

      {/* Property type */}
      <div className={styles.group}>
        <span className={styles.label}>Type</span>
        <div className={styles.chipGroup}>
          {PROPERTY_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`${styles.chip} ${propertyTypes.includes(opt.value) ? styles.chipActive : ''}`}
              onClick={() => toggleType(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* More filters */}
      <div className={styles.advancedWrap} ref={advancedRef}>
        <button
          type="button"
          className={`${styles.moreBtn} ${activeAdvancedCount > 0 ? styles.moreBtnActive : ''}`}
          onClick={() => setAdvancedOpen((o) => !o)}
        >
          <SlidersHorizontal size={14} strokeWidth={1.8} />
          More
          {activeAdvancedCount > 0 && (
            <span className={styles.moreBadge}>{activeAdvancedCount}</span>
          )}
        </button>
        {advancedOpen && (
          <div className={styles.advancedPanel} role="dialog">
            <div className={styles.advancedRow}>
              <label className={styles.advancedLabel}>Min sqft</label>
              <input
                type="number"
                min={0}
                step={100}
                className={styles.numberInput}
                placeholder="any"
                value={minSqft ?? ''}
                onChange={(e) => onMinSqftChange(e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
            <div className={styles.advancedRow}>
              <label className={styles.advancedLabel}>Built after</label>
              <input
                type="number"
                min={1800}
                max={2100}
                step={1}
                className={styles.numberInput}
                placeholder="any year"
                value={minYearBuilt ?? ''}
                onChange={(e) => onMinYearBuiltChange(e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Result count pinned right */}
      <div className={styles.countWrap}>
        <span className={styles.count}>
          {resultCount} {resultCount === 1 ? 'home' : 'homes'} in range
        </span>
      </div>
    </div>
  )
}
