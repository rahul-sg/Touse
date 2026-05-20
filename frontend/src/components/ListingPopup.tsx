import { Popup } from 'react-map-gl/maplibre'
import type { Listing } from '../types'
import styles from './ListingPopup.module.css'

interface Props {
  listing: Listing
  onClose: () => void
  isAffordable?: boolean
  userMaxPrice?: number
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

/**
 * Estimate the annual income needed to comfortably buy a home at listingPrice,
 * given a known down payment and rate. Uses the 28% front-end DTI rule.
 */
function computeRequiredIncome(
  listingPrice: number,
  downPayment: number,
  ratePercent: number
): number {
  const rate = ratePercent / 100
  const loan = listingPrice - downPayment
  if (loan <= 0) return 0
  const r = rate / 12
  const n = 360
  const monthlyPayment = (loan * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
  // Front-end DTI: monthly payment ≤ 28% of gross monthly income
  const requiredMonthlyIncome = monthlyPayment / 0.28
  return requiredMonthlyIncome * 12
}

export default function ListingPopup({ listing, onClose, isAffordable = true, userMaxPrice }: Props) {
  // Default assumptions for the "what you'd need" section
  const assumedDownPayment = listing.price * 0.1 // 10% down
  const assumedRate = 7.0 // fallback rate

  const requiredIncome =
    !isAffordable
      ? computeRequiredIncome(listing.price, assumedDownPayment, assumedRate)
      : null

  const shortfall = userMaxPrice != null ? listing.price - userMaxPrice : null

  return (
    <Popup
      latitude={listing.lat}
      longitude={listing.lng}
      anchor="bottom"
      offset={16}
      onClose={onClose}
      closeOnClick={false}
      maxWidth="280px"
    >
      <div className={styles.popup}>
        <p className={`${styles.price} ${!isAffordable ? styles.priceUnaffordable : ''}`}>
          {fmt(listing.price)}
          {!isAffordable && <span className={styles.outOfRange}> · over budget</span>}
        </p>
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

        {!isAffordable && requiredIncome != null && (
          <div className={styles.needSection}>
            <p className={styles.needTitle}>What you'd need:</p>
            <ul className={styles.needList}>
              <li>
                <strong>{fmt(requiredIncome)}</strong> annual income (at 28% DTI, 10% down,{' '}
                {assumedRate}% rate)
              </li>
              {shortfall != null && shortfall > 0 && (
                <li>
                  <strong>{fmt(shortfall)}</strong> more than your current max price
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </Popup>
  )
}
