import { useState, useCallback, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import TouseMap from '../components/TouseMap'
import ListingSidebar from '../components/ListingSidebar'
import ZipForecastPanel from '../components/ZipForecastPanel'
import { useListings } from '../hooks/useListings'
import { lookupZip, getNearestZip } from '../utils/api'
import styles from './MapView.module.css'

interface LocationState {
  maxPrice?: number
  fromOnboarding?: boolean
  scenarioName?: string
  /** When navigating from ScenarioDetail, center the map on the scenario's ZIP instead of user's target_zip */
  targetZip?: string
}

interface ZipInfo {
  zip_code: string
  city: string | null
  state_code: string | null
}

const DEFAULT_MAX_PRICE = 600_000
const DEFAULT_CENTER = { lat: 39.8283, lng: -98.5795 }
const ZIP_DEBOUNCE_MS = 700

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

  const [viewport, setViewport] = useState(DEFAULT_CENTER)
  const [activeZip, setActiveZip] = useState<string | null>(null)
  const [zipInfo, setZipInfo] = useState<ZipInfo | null>(null)
  const [zipResolving, setZipResolving] = useState(false)
  const [mapCenter, setMapCenter] = useState<{ lat: number; lng: number } | null>(null)
  // Track whether the initial ZIP lookup is still pending, so we don't fire
  // a wasted listings query for the US-center default viewport.
  const [zipLookupPending, setZipLookupPending] = useState(false)

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Prefer scenario ZIP (when navigating from ScenarioDetail) → then user's profile target_zip
  const initialZip = state?.targetZip ?? user?.target_zip ?? null

  // Resolve initialZip → lat/lng on mount so the map centers on the right area
  useEffect(() => {
    if (!initialZip) return
    setZipLookupPending(true)
    lookupZip(initialZip)
      .then(result => {
        setViewport({ lat: result.lat, lng: result.lng })
        setMapCenter({ lat: result.lat, lng: result.lng })
        setActiveZip(initialZip)
        setZipInfo({ zip_code: initialZip, city: result.city, state_code: result.state_code })
      })
      .catch(() => {
        // ZIP not found — stay at default center
      })
      .finally(() => {
        setZipLookupPending(false)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialZip])

  // Clean up debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [])

  const { data: listings = [], isFetching } = useListings(
    zipLookupPending
      ? null  // suppress the wasted US-center query while the target ZIP is resolving
      : { lat: viewport.lat, lng: viewport.lng, maxPrice, minBeds }
  )

  const handleViewportChange = useCallback((lat: number, lng: number) => {
    setViewport({ lat, lng })

    // Debounce: wait until panning stops before hitting the nearest-ZIP endpoint
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    setZipResolving(true)

    debounceTimer.current = setTimeout(async () => {
      const result = await getNearestZip(lat, lng)
      setZipResolving(false)
      if (result) {
        setActiveZip(result.zip_code)
        setZipInfo({ zip_code: result.zip_code, city: result.city, state_code: result.state_code })
      }
    }, ZIP_DEBOUNCE_MS)
  }, [])

  const forecastPanel = zipResolving
    ? <div className={styles.zipResolving}>Detecting area…</div>
    : activeZip
      ? <ZipForecastPanel zip={activeZip} />
      : null

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
          zipForecastPanel={forecastPanel}
        />
        <div className={styles.mapWrap}>
          {/* ZIP overlay badge — shows which area is being forecasted */}
          {zipInfo && (
            <div className={styles.zipOverlay}>
              <span className={styles.zipOverlayPin}>📍</span>
              <span className={styles.zipOverlayCode}>{zipInfo.zip_code}</span>
              {zipInfo.city && (
                <span className={styles.zipOverlayCity}>
                  {zipInfo.city}{zipInfo.state_code ? `, ${zipInfo.state_code}` : ''}
                </span>
              )}
              {zipResolving && <span className={styles.zipOverlaySpinner} />}
            </div>
          )}

          <TouseMap
            listings={listings}
            onViewportChange={handleViewportChange}
            maxPrice={maxPrice}
            centerOn={mapCenter}
          />
        </div>
      </div>
    </div>
  )
}
