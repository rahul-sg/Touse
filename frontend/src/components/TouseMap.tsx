import { useRef, useCallback, useState } from 'react'
import Map, { type MapRef, NavigationControl } from 'react-map-gl/mapbox'
import type { BBox } from 'geojson'
import Supercluster from 'supercluster'
import type { Listing } from '../types'
import ListingMarker from './ListingMarker'
import ListingPopup from './ListingPopup'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? ''

interface ViewState {
  longitude: number
  latitude: number
  zoom: number
}

interface Props {
  listings: Listing[]
  onViewportChange?: (lat: number, lng: number, zoom: number) => void
}

type GeoFeature = GeoJSON.Feature<GeoJSON.Point, Listing & { cluster: false }>

function toFeatures(listings: Listing[]): GeoFeature[] {
  return listings.map((l) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [l.lng, l.lat] },
    properties: { ...l, cluster: false },
  }))
}

export default function TouseMap({ listings, onViewportChange }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [viewState, setViewState] = useState<ViewState>({
    longitude: -98.5795,
    latitude: 39.8283,
    zoom: 4,
  })
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
      mapStyle="mapbox://styles/mapbox/light-v11"
      mapboxAccessToken={MAPBOX_TOKEN}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" />

      {clusters.map((cluster) => {
        const [lng, lat] = cluster.geometry.coordinates
        const { cluster: isCluster, cluster_id, point_count } = cluster.properties as any

        if (isCluster) {
          return (
            <ListingMarker
              key={`cluster-${cluster_id}`}
              lat={lat}
              lng={lng}
              count={point_count}
              onClick={() => handleClusterClick(cluster_id, lng, lat)}
            />
          )
        }

        const listing = cluster.properties as Listing
        return (
          <ListingMarker
            key={listing.id}
            lat={lat}
            lng={lng}
            price={listing.price}
            onClick={() => setSelected(listing)}
            isSelected={selected?.id === listing.id}
          />
        )
      })}

      {selected && (
        <ListingPopup
          listing={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </Map>
  )
}
