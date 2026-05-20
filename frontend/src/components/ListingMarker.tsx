import { Marker } from 'react-map-gl/mapbox'
import styles from './ListingMarker.module.css'

interface Props {
  lat: number
  lng: number
  price?: number
  count?: number
  onClick: () => void
  isSelected?: boolean
}

function fmtPrice(price: number): string {
  if (price >= 1_000_000) return `$${(price / 1_000_000).toFixed(1)}M`
  if (price >= 1_000) return `$${Math.round(price / 1_000)}K`
  return `$${price}`
}

export default function ListingMarker({ lat, lng, price, count, onClick, isSelected }: Props) {
  const isCluster = count !== undefined

  return (
    <Marker latitude={lat} longitude={lng} anchor="bottom" onClick={onClick}>
      {isCluster ? (
        <div className={styles.cluster}>
          <span>{count}</span>
        </div>
      ) : (
        <div className={`${styles.pin} ${isSelected ? styles.selected : ''}`}>
          <span>{fmtPrice(price ?? 0)}</span>
        </div>
      )}
    </Marker>
  )
}
