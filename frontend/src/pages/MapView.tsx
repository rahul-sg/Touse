import { useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import TouseMap from '../components/TouseMap'
import ListingSidebar from '../components/ListingSidebar'
import { useListings } from '../hooks/useListings'
import styles from './MapView.module.css'

interface LocationState {
  maxPrice?: number
  fromOnboarding?: boolean
}

const DEFAULT_MAX_PRICE = 600_000
const DEFAULT_CENTER = { lat: 39.8283, lng: -98.5795 }

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function MapView() {
  const location = useLocation()
  const state = location.state as LocationState | null

  const fromOnboarding = state?.fromOnboarding ?? false
  const [maxPrice, setMaxPrice] = useState(state?.maxPrice ?? DEFAULT_MAX_PRICE)
  const [minBeds, setMinBeds] = useState(1)
  const [viewport, setViewport] = useState(DEFAULT_CENTER)

  const { data: listings = [], isFetching } = useListings({
    lat: viewport.lat,
    lng: viewport.lng,
    maxPrice,
    minBeds,
  })

  const handleViewportChange = useCallback((lat: number, lng: number) => {
    setViewport({ lat, lng })
  }, [])

  return (
    <div className={styles.page}>
      {fromOnboarding && (
        <div className={styles.onboardingBanner}>
          Showing homes in your range — <strong>{fmt(maxPrice)}</strong> and under. Grayed listings
          are slightly above your budget.
        </div>
      )}
      <div className={styles.body}>
        <ListingSidebar
          listings={listings}
          isLoading={isFetching}
          maxPrice={maxPrice}
          onMaxPriceChange={setMaxPrice}
          minBeds={minBeds}
          onMinBedsChange={setMinBeds}
        />
        <div className={styles.mapWrap}>
          <TouseMap
            listings={listings}
            onViewportChange={handleViewportChange}
            maxPrice={maxPrice}
          />
        </div>
      </div>
    </div>
  )
}
