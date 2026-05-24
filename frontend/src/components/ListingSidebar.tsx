import { useState } from 'react'
import type { ReactNode } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import type { Listing, PropertyType } from '../types'
import styles from './ListingSidebar.module.css'

interface Props {
  listings: Listing[]
  isLoading: boolean
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
  zipForecastPanel?: ReactNode
  /** Clicking a card asks the map to fly to that listing. */
  onListingClick?: (listing: Listing) => void
  /** id of the listing currently focused on the map, for card highlighting. */
  selectedId?: string | null
}

const PROPERTY_TYPE_OPTIONS: { value: PropertyType; label: string }[] = [
  { value: 'single_family', label: 'House' },
  { value: 'condo',         label: 'Condo' },
  { value: 'townhouse',     label: 'Townhouse' },
  { value: 'multi_family',  label: 'Multi-fam' },
  { value: 'mobile',        label: 'Mobile' },
  { value: 'land',          label: 'Land' },
]

const PROPERTY_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  PROPERTY_TYPE_OPTIONS.map(o => [o.value, o.label]),
)

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtSqft(n: number) {
  return n.toLocaleString('en-US') + ' sqft'
}

export default function ListingSidebar({
  listings,
  isLoading,
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
  zipForecastPanel,
  onListingClick,
  selectedId,
}: Props) {
  const [advancedOpen, setAdvancedOpen] = useState(false)

  function toggleType(t: PropertyType) {
    const next = propertyTypes.includes(t)
      ? propertyTypes.filter(x => x !== t)
      : [...propertyTypes, t]
    onPropertyTypesChange(next)
  }

  const activeAdvancedCount = (minSqft ? 1 : 0) + (minYearBuilt ? 1 : 0)

  return (
    <aside className={styles.sidebar}>
      <div className={styles.filters}>
        <h2 className={styles.heading}>
          Listings
          {listings.length > 0 && (
            <span className={styles.resultCount}>{listings.length} in range</span>
          )}
        </h2>

        <div className={styles.filterRow}>
          <label className={styles.filterLabel}>Max Price</label>
          <div className={styles.filterControl}>
            <input
              type="range"
              min={100_000}
              max={3_000_000}
              step={10_000}
              value={maxPrice}
              onChange={(e) => onMaxPriceChange(Number(e.target.value))}
            />
            <span className={styles.filterValue}>{fmt(maxPrice)}</span>
          </div>
        </div>

        <div className={styles.filterRow}>
          <label className={styles.filterLabel}>Min Beds</label>
          <div className={styles.bedBtns}>
            {[1, 2, 3, 4].map((n) => (
              <button
                key={n}
                className={`${styles.bedBtn} ${minBeds === n ? styles.bedBtnActive : ''}`}
                onClick={() => onMinBedsChange(n)}
              >
                {n}+
              </button>
            ))}
          </div>
        </div>

        <div className={styles.filterRow}>
          <label className={styles.filterLabel}>Property Type</label>
          <div className={styles.chipRow}>
            {PROPERTY_TYPE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`${styles.chip} ${propertyTypes.includes(opt.value) ? styles.chipActive : ''}`}
                onClick={() => toggleType(opt.value)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          className={styles.advancedToggle}
          onClick={() => setAdvancedOpen(o => !o)}
        >
          <SlidersHorizontal size={14} strokeWidth={1.8} />
          More filters
          {activeAdvancedCount > 0 && (
            <span className={styles.advancedBadge}>{activeAdvancedCount}</span>
          )}
        </button>

        {advancedOpen && (
          <div className={styles.advancedPanel}>
            <div className={styles.filterRow}>
              <label className={styles.filterLabel}>Min Sqft</label>
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
            <div className={styles.filterRow}>
              <label className={styles.filterLabel}>Built After</label>
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

      {zipForecastPanel && (
        <div className={styles.forecastSlot}>{zipForecastPanel}</div>
      )}

      <div className={styles.list}>
        {isLoading && (
          <div className={styles.state}>
            <div className={styles.spinner} />
            <p>Loading listings…</p>
          </div>
        )}

        {!isLoading && listings.length === 0 && (
          <div className={styles.state}>
            <p>No listings found in this area for your budget.</p>
            <p className={styles.hint}>Try zooming out, raising max price, or relaxing the filters.</p>
          </div>
        )}

        {!isLoading && listings.map((l) => (
          <div
            key={l.id}
            className={`${styles.card} ${selectedId === l.id ? styles.cardSelected : ''}`}
            onClick={() => onListingClick?.(l)}
          >
            {l.photo_url
              ? <img src={l.photo_url} alt={l.address} className={styles.cardPhoto} loading="lazy" />
              : <div className={styles.cardPhotoPlaceholder}>No photo</div>
            }
            <div className={styles.cardBody}>
              <div className={styles.cardPriceRow}>
                <span className={styles.cardPrice}>{fmt(l.price)}</span>
                {l.property_type && (
                  <span className={styles.cardTypeBadge}>
                    {PROPERTY_TYPE_LABEL[String(l.property_type)] ?? String(l.property_type)}
                  </span>
                )}
              </div>
              <p className={styles.cardMeta}>
                {l.beds ?? '—'} bd &nbsp;·&nbsp; {l.baths ?? '—'} ba
                {l.sqft && <> &nbsp;·&nbsp; {fmtSqft(l.sqft)}</>}
                {l.year_built && <> &nbsp;·&nbsp; built {l.year_built}</>}
              </p>
              <p className={styles.cardAddress}>{l.address}</p>
              {l.listing_url && l.listing_url !== '#' && (
                <a
                  className={styles.cardLink}
                  href={l.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  View listing ↗
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}
