import type { ReactNode } from 'react'
import type { Listing, PropertyType } from '../types'
import styles from './ListingSidebar.module.css'

interface Props {
  listings: Listing[]
  isLoading: boolean
  zipForecastPanel?: ReactNode
  /** Clicking a card asks the map to fly to that listing. */
  onListingClick?: (listing: Listing) => void
  /** id of the listing currently focused on the map, for card highlighting. */
  selectedId?: string | null
}

const PROPERTY_TYPE_LABEL: Record<PropertyType, string> = {
  single_family: 'House',
  condo:         'Condo',
  townhouse:     'Townhouse',
  multi_family:  'Multi-fam',
  mobile:        'Mobile',
  land:          'Land',
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtSqft(n: number) {
  return n.toLocaleString('en-US') + ' sqft'
}

export default function ListingSidebar({
  listings,
  isLoading,
  zipForecastPanel,
  onListingClick,
  selectedId,
}: Props) {
  return (
    <aside className={styles.sidebar}>
      {zipForecastPanel && (
        <div className={styles.forecastSlot}>{zipForecastPanel}</div>
      )}

      <div className={styles.listHeader}>
        <h2 className={styles.heading}>
          Listings
          {listings.length > 0 && (
            <span className={styles.resultCount}>{listings.length} in range</span>
          )}
        </h2>
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
            <p className={styles.hint}>Try zooming out, raising max price, or relaxing the filters above.</p>
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
                    {PROPERTY_TYPE_LABEL[l.property_type as PropertyType] ?? String(l.property_type)}
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
