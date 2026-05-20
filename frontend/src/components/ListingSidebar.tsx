import type { Listing } from '../types'
import styles from './ListingSidebar.module.css'

interface Props {
  listings: Listing[]
  isLoading: boolean
  maxPrice: number
  onMaxPriceChange: (v: number) => void
  minBeds: number
  onMinBedsChange: (v: number) => void
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function ListingSidebar({
  listings,
  isLoading,
  maxPrice,
  onMaxPriceChange,
  minBeds,
  onMinBedsChange,
}: Props) {
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
      </div>

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
            <p className={styles.hint}>Try zooming out or increasing your max price.</p>
          </div>
        )}

        {!isLoading && listings.map((l) => (
          <div key={l.id} className={styles.card}>
            {(l as any).photo_url
              ? <img src={(l as any).photo_url} alt={l.address} className={styles.cardPhoto} loading="lazy" />
              : <div className={styles.cardPhotoPlaceholder}>No photo</div>
            }
            <div className={styles.cardBody}>
              <span className={styles.cardPrice}>{fmt(l.price)}</span>
              <p className={styles.cardMeta}>
                {l.beds ?? '—'} bd &nbsp;·&nbsp; {l.baths ?? '—'} ba
              </p>
              <p className={styles.cardAddress}>{l.address}</p>
              {l.listing_url && l.listing_url !== '#' && (
                <a
                  className={styles.cardLink}
                  href={l.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
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
