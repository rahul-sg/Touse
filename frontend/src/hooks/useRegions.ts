import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { Region } from '../types'

async function searchRegions(q: string): Promise<Region[]> {
  if (q.length < 2) return []
  const { data } = await api.get<Region[]>('/api/v1/regions/search', { params: { q } })
  return data
}

export function useRegions(q: string) {
  return useQuery({
    queryKey: ['regions', q],
    queryFn: () => searchRegions(q),
    enabled: q.length >= 2,
    staleTime: 1000 * 60 * 5,
  })
}
