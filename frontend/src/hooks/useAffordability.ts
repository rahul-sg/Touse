import { useMutation } from '@tanstack/react-query'
import { api } from '../utils/api'
import type { AffordabilityResult } from '../types'

export interface AffordabilityInput {
  annual_income: number
  savings: number
  monthly_debt: number
  credit_score: number
  down_payment: number
  zip_code: string
}

async function fetchAffordability(input: AffordabilityInput): Promise<AffordabilityResult> {
  const { data } = await api.post<AffordabilityResult>('/api/v1/affordability', input)
  return data
}

export function useAffordability() {
  return useMutation({ mutationFn: fetchAffordability })
}
