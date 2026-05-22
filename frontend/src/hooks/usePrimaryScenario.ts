import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useScenarios } from './useScenarios'
import { getMe } from '../utils/api'
import type { Scenario } from '../types'

/**
 * Resolves the user's primary scenario — the one that drives the dashboard
 * headline, the map's default centering, and the ZIP forecast.
 *
 * Priority: the user's explicit pick → their only scenario → none.
 */
export function usePrimaryScenario(): {
  primaryScenario: Scenario | null
  scenarios: Scenario[]
  isLoading: boolean
} {
  const { user } = useAuth()
  const { data: scenarios = [], isLoading } = useScenarios(user?.user_id)
  const [primaryPublicId, setPrimaryPublicId] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    let cancelled = false
    getMe(user.user_id)
      .then(me => { if (!cancelled) setPrimaryPublicId(me.primary_scenario_public_id ?? null) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [user])

  const primaryScenario = useMemo<Scenario | null>(() => {
    if (scenarios.length === 0) return null
    if (primaryPublicId) {
      const found = scenarios.find(s => s.public_id === primaryPublicId)
      if (found) return found
    }
    return scenarios.length === 1 ? scenarios[0] : null
  }, [scenarios, primaryPublicId])

  return { primaryScenario, scenarios, isLoading }
}
