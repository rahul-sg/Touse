import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { MarketIndicators } from '../types'

async function fetchMarket(metroId: string): Promise<MarketIndicators> {
  const { data } = await api.get<MarketIndicators>(`/api/v1/market/${metroId}`)
  return data
}

export function useMarket(metroId: string | null) {
  return useQuery({
    queryKey: ['market', metroId],
    queryFn: () => fetchMarket(metroId!),
    enabled: !!metroId,
    staleTime: 1000 * 60 * 60,
  })
}
