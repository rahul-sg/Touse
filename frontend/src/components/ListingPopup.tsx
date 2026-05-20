import { Popup } from 'react-map-gl/mapbox'
import type { Listing } from '../types'
import styles from './ListingPopup.module.css'

interface Props {
  listing: Listing
  onClose: () => void
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function ListingPopup({ listing, onClose }: Props) {
  return (
    <Popup
      latitude={listing.lat}
      longitude={listing.lng}
      anchor="bottom"
      offset={16}
      onClose={onClose}
      closeOnClick={false}
      maxWidth="260px"
    >
      <div className={styles.popup}>
        <p className={styles.price}>{fmt(listing.price)}</p>
        <p className={styles.address}>{listing.address}</p>
        <p className={styles.details}>
          {listing.beds} bd · {listing.baths ?? '—'} ba
        </p>
        {listing.listing_url && listing.listing_url !== '#' && (
          <a
            className={styles.link}
            href={listing.listing_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            View listing →
          </a>
        )}
      </div>
    </Popup>
  )
}
