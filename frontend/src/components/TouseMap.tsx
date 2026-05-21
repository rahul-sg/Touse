import { useRef, useCallback, useState, useEffect } from 'react'
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

function toFeatures(listings: Listing[]): GeoFeature[] {
  return listings.map((l) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [l.lng, l.lat] },
    properties: { ...l, cluster: false },
  }))
}

export default function TouseMap({ listings, onViewportChange, maxPrice, centerOn }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [viewState, setViewState] = useState<ViewState>({
    longitude: -98.5795,
    latitude: 39.8283,
    zoom: 4,
  })

  // Fly to centerOn when it changes (e.g. user's target ZIP resolved)
  useEffect(() => {
    if (!centerOn) return
    mapRef.current?.flyTo({
      center: [centerOn.lng, centerOn.lat],
      zoom: 11,
      duration: 1000,
    })
  }, [centerOn?.lat, centerOn?.lng])
  const [selected, setSelected] = useState<Listing | null>(null)

  const supercluster = new Supercluster({ radius: 60, maxZoom: 14 })
  const features = toFeatures(listings)
  supercluster.load(features)

  const map = mapRef.current?.getMap()
  const rawBounds = map?.getBounds()
  const bounds: BBox = rawBounds
    ? [rawBounds.getWest(), rawBounds.getSouth(), rawBounds.getEast(), rawBounds.getNorth()]
    : [-180, -85, 180, 85]

  const clusters = supercluster.getClusters(bounds, Math.floor(viewState.zoom))

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
