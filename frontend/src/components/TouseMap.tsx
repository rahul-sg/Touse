import { useRef, useCallback, useState, useEffect, useMemo } from 'react'
import Map, { type MapRef, NavigationControl } from 'react-map-gl/maplibre'
import type { BBox } from 'geojson'
import Supercluster from 'supercluster'
import type { Listing } from '../types'
import ListingMarker from './ListingMarker'
import ListingPopup from './ListingPopup'
import 'maplibre-gl/dist/maplibre-gl.css'

// OpenFreeMap — free vector tiles, no API key required
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

interface ViewState {
  longitude: number
  latitude: number
  zoom: number
}

interface Props {
  listings: Listing[]
  onViewportChange?: (lat: number, lng: number, zoom: number) => void
  maxPrice?: number
  centerOn?: { lat: number; lng: number } | null
}

type GeoFeature = GeoJSON.Feature<GeoJSON.Point, Listing & { cluster: false }>

/**
 * Simple hash of a string → small float in range [0, 1)
 * Used to generate a deterministic jitter so that listings returned with the
 * same lat/lng (RapidAPI falls back to the ZIP centroid when a property has no
 * coordinates) spread out visually instead of all stacking at one pin.
 */
function hashFrac(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  }
  return (h >>> 0) / 0xffffffff
}

function toFeatures(listings: Listing[]): GeoFeature[] {
  // Detect whether listings are sharing the same lat/lng (API gave no per-property coords).
  // If so, add a small deterministic spread (~200 m radius) so each pin is individually clickable.
  const latSet = new Set(listings.map((l) => l.lat))
  const lngSet = new Set(listings.map((l) => l.lng))
  const allSamePoint = listings.length > 1 && latSet.size === 1 && lngSet.size === 1

  return listings.map((l) => {
    let lat = l.lat
    let lng = l.lng
    if (allSamePoint) {
      // ±0.0015° ≈ ±165 m — deterministic per listing so pins don't jump on re-render
      const angle = hashFrac(l.id + 'a') * 2 * Math.PI
      const radius = 0.0008 + hashFrac(l.id + 'r') * 0.0012
      lat = l.lat + Math.sin(angle) * radius
      lng = l.lng + Math.cos(angle) * radius
    }
    return {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: { ...l, cluster: false },
    }
  })
}

export default function TouseMap({ listings, onViewportChange, maxPrice, centerOn }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [viewState, setViewState] = useState<ViewState>({
    longitude: -98.5795,
    latitude: 39.8283,
    zoom: 4,
  })

  // Fly to centerOn — but only after the map has fully loaded.
  // If centerOn arrives before the map is ready, we re-run this effect
  // once mapLoaded flips to true.
  useEffect(() => {
    if (!centerOn || !mapLoaded) return
    mapRef.current?.flyTo({
      center: [centerOn.lng, centerOn.lat],
      zoom: 11,
      duration: 1000,
    })
  }, [centerOn?.lat, centerOn?.lng, mapLoaded])

  const [selected, setSelected] = useState<Listing | null>(null)

  // Memoize supercluster so it isn't recreated on every render
  const supercluster = useMemo(() => {
    const sc = new Supercluster({ radius: 60, maxZoom: 14 })
    sc.load(toFeatures(listings))
    return sc
  }, [listings])

  const map = mapRef.current?.getMap()
  const rawBounds = map?.getBounds()
  const bounds: BBox = rawBounds
    ? [rawBounds.getWest(), rawBounds.getSouth(), rawBounds.getEast(), rawBounds.getNorth()]
    : [-180, -85, 180, 85]

  const clusters = supercluster.getClusters(bounds, Math.floor(viewState.zoom))

  const handleMapLoad = useCallback(() => {
    setMapLoaded(true)
  }, [])

  const handleMove = useCallback(
    (evt: { viewState: ViewState }) => {
      setViewState(evt.viewState)
    },
    []
  )

  // Only notify parent when the map has fully stopped moving (end of pan, zoom, or flyTo).
  // This prevents flooding useListings with a query per animation frame.
  const handleMoveEnd = useCallback(
    (evt: { viewState: ViewState }) => {
      onViewportChange?.(evt.viewState.latitude, evt.viewState.longitude, evt.viewState.zoom)
    },
    [onViewportChange]
  )

  const handleClusterClick = useCallback(
    (clusterId: number, lng: number, lat: number) => {
      const zoom = supercluster.getClusterExpansionZoom(clusterId)
      mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 400 })
    },
    [supercluster]
  )

  return (
    <Map
      ref={mapRef}
      {...viewState}
      onLoad={handleMapLoad}
      onMove={handleMove}
      onMoveEnd={handleMoveEnd}
      mapStyle={MAP_STYLE}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" />

      {clusters.map((cluster) => {
        const [lng, lat] = cluster.geometry.coordinates
        const { cluster: isCluster, cluster_id, point_count } = cluster.properties as Record<string, unknown>

        if (isCluster) {
          return (
            <ListingMarker
              key={`cluster-${cluster_id as number}`}
              lat={lat}
              lng={lng}
              count={point_count as number}
              onClick={() => handleClusterClick(cluster_id as number, lng, lat)}
            />
          )
        }

        const listing = cluster.properties as Listing
        const isAffordable = maxPrice == null || listing.price <= maxPrice

        return (
          <ListingMarker
            key={listing.id}
            lat={lat}
            lng={lng}
            price={listing.price}
            onClick={() => setSelected(listing)}
            isSelected={selected?.id === listing.id}
            isAffordable={isAffordable}
          />
        )
      })}

      {selected && (
        <ListingPopup
          listing={selected}
          onClose={() => setSelected(null)}
          isAffordable={maxPrice == null || selected.price <= maxPrice}
          userMaxPrice={maxPrice}
        />
      )}
    </Map>
  )
}
