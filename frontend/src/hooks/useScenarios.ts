import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getScenarios, createScenario, updateScenario, deleteScenario } from '../utils/api'
import type { ScenarioPayload } from '../utils/api'

export function useScenarios(userId: number | undefined) {
  return useQuery({
    queryKey: ['scenarios', userId],
    queryFn: () => getScenarios(userId!),
    enabled: !!userId,
  })
}

export function useCreateScenario(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ScenarioPayload) => createScenario(userId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenarios', userId] }),
  })
}

export function useDeleteScenario(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (publicId: string) => deleteScenario(publicId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenarios', userId] }),
  })
}

export function useUpdateScenario(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ publicId, ...payload }: { publicId: string } & Partial<ScenarioPayload>) =>
      updateScenario(publicId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenarios', userId] }),
  })
}
