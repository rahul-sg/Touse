import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Listing } from '../types'

interface ListingsParams {
  lat: number
  lng: number
  radiusMiles?: number
  maxPrice: number
  minBeds?: number
}

async function fetchListings(params: ListingsParams): Promise<Listing[]> {
  const { data } = await api.get<Listing[]>('/api/v1/listings', {
    params: {
      lat: params.lat,
      lng: params.lng,
      radius_miles: params.radiusMiles ?? 10,
      max_price: params.maxPrice,
      min_beds: params.minBeds ?? 1,
    },
  })
  return data
}

export function useListings(params: ListingsParams | null) {
  return useQuery({
    queryKey: ['listings', params],
    queryFn: () => fetchListings(params!),
    enabled: !!params && params.maxPrice > 0,
    staleTime: 1000 * 60 * 30,
  })
}
