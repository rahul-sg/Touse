import { useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import TouseMap from '../components/TouseMap'
import ListingSidebar from '../components/ListingSidebar'
import { useListings } from '../hooks/useListings'
import styles from './MapView.module.css'

interface LocationState {
  maxPrice?: number
  fromOnboarding?: boolean
  scenarioName?: string
  scenarioId?: number
}

const DEFAULT_MAX_PRICE = 600_000
const DEFAULT_CENTER = { lat: 39.8283, lng: -98.5795 }

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function MapView() {
  const location = useLocation()
  const { user } = useAuth()
  const state = location.state as LocationState | null

  const fromOnboarding = state?.fromOnboarding ?? false
  const scenarioName = state?.scenarioName ?? null
  const [maxPrice, setMaxPrice] = useState(state?.maxPrice ?? DEFAULT_MAX_PRICE)
  const [minBeds, setMinBeds] = useState(1)

  // Use user's target_zip as a hint for initial center when available.
  // Phase 5 will resolve ZIP → lat/lng via the nearest-zip endpoint.
  // For now, fall back to geographic center of the USA.
  const [viewport, setViewport] = useState(DEFAULT_CENTER)

  // Store target_zip for display in the forecast panel (Phase 8)
  const targetZip = user?.target_zip ?? null

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
      {(fromOnboarding || scenarioName) && (
        <div className={styles.onboardingBanner}>
          {scenarioName ? (
            <>
              Filtering by <strong>{scenarioName}</strong> — homes up to{' '}
              <strong>{fmt(maxPrice)}</strong>. Grayed listings are above your budget.
            </>
          ) : (
            <>
              Showing homes in your range — <strong>{fmt(maxPrice)}</strong> and under. Grayed
              listings are slightly above your budget.
            </>
          )}
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
