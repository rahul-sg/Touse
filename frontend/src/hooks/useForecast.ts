import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { MetroForecast } from '../types'

async function fetchForecast(metroId: string): Promise<MetroForecast> {
  const { data } = await api.get<MetroForecast>(`/api/v1/forecast/${metroId}`)
  return data
}

export function useForecast(metroId: string | null) {
  return useQuery({
    queryKey: ['forecast', metroId],
    queryFn: () => fetchForecast(metroId!),
    enabled: !!metroId,
    staleTime: 1000 * 60 * 60, // forecast data is stable for an hour
  })
}
