import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Listing, PropertyType } from '../types'

interface ListingsParams {
  lat: number
  lng: number
  radiusMiles?: number
  maxPrice: number
  minBeds?: number
  /** Filter to these property types — empty/undefined = all types. */
  propertyTypes?: PropertyType[]
  minSqft?: number
  minYearBuilt?: number
}

async function fetchListings(params: ListingsParams): Promise<Listing[]> {
  const { data } = await api.get<Listing[]>('/api/v1/listings', {
    params: {
      lat: params.lat,
      lng: params.lng,
      radius_miles: params.radiusMiles ?? 10,
      max_price: params.maxPrice,
      min_beds: params.minBeds ?? 1,
      // FastAPI parses repeated `?property_types=condo&property_types=single_family`
      // when this is sent as an array — axios serializes arrays that way by default.
      ...(params.propertyTypes && params.propertyTypes.length > 0
        ? { property_types: params.propertyTypes }
        : {}),
      ...(params.minSqft ? { min_sqft: params.minSqft } : {}),
      ...(params.minYearBuilt ? { min_year_built: params.minYearBuilt } : {}),
    },
    // Repeat keys for arrays — required so FastAPI sees `property_types` as a list.
    paramsSerializer: { indexes: null },
  })
  return data
}

export function useListings(params: ListingsParams | null) {
  return useQuery({
    queryKey: ['listings', params],
    queryFn: () => fetchListings(params!),
    enabled: !!params && params.maxPrice > 0,
    staleTime: 1000 * 60 * 5,
  })
}
