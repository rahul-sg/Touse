import { useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import TouseMap from '../components/TouseMap'
import ListingSidebar from '../components/ListingSidebar'
import { useListings } from '../hooks/useListings'
import styles from './MapView.module.css'

interface LocationState {
  maxPrice?: number
}

const DEFAULT_MAX_PRICE = 600_000
const DEFAULT_CENTER = { lat: 39.8283, lng: -98.5795 }

export default function MapView() {
  const location = useLocation()
  const state = location.state as LocationState | null

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
        />
        {!import.meta.env.VITE_MAPBOX_TOKEN && (
          <div className={styles.tokenWarning}>
            Add <code>VITE_MAPBOX_TOKEN</code> to your <code>.env</code> to enable the map.
          </div>
        )}
      </div>
    </div>
  )
}
