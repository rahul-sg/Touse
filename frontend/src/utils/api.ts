import axios from 'axios'
import type { Scenario, RentalAffordability } from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export interface RegisterPayload {
  first_name: string
  last_name: string
  email: string
  username: string
  password: string
  target_zip?: string
}

export interface ProfilePayload {
  annual_income: number
  savings: number
  down_payment: number
  credit_score: number
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string
  liquid_savings?: number
  brokerage_value?: number
  retirement_value?: number
  monthly_take_home?: number
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  first_name: string
  target_zip: string | null
}

export interface ReadinessRequest {
  annual_income: number
  savings?: number
  down_payment?: number
  credit_score?: number
  monthly_debt_car?: number
  monthly_debt_student?: number
  monthly_debt_credit?: number
  monthly_debt_other?: number
  cached_max_price?: number
  rate_used?: number
  liquid_savings?: number
  target_zip?: string
}

export interface ReadinessResult {
  score: number
  components: {
    dti_pts: number
    dp_pts: number
    credit_pts: number
    cushion_pts: number
    market_fit_pts: number
  }
  dti_ratio_pct: number
  dti_ceiling_pct: number
  dp_pct: number
  cushion_months: number
  credit_label: string
  rate_used: number
  target_price: number
  market_median: number | null
  market_fit_label: string | null
  market_fit_ratio_pct: number | null
  actions: string[]
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/v1/auth/register', payload)
  return data
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/v1/auth/login', { email, password })
  return data
}

export async function saveProfile(userId: number, payload: ProfilePayload): Promise<void> {
  await api.post(`/api/v1/auth/profile/${userId}`, payload)
}

export async function getMe(userId: number) {
  const { data } = await api.get(`/api/v1/auth/me/${userId}`)
  return data
}

export interface ScenarioPayload {
  name: string
  scenario_type: 'buy' | 'rent'
  annual_income?: number
  savings?: number
  down_payment?: number
  credit_score?: number
  monthly_debt_car?: number
  monthly_debt_student?: number
  monthly_debt_credit?: number
  monthly_debt_other?: number
  zip_code?: string
  loan_type?: string
  cached_max_price?: number
  cached_monthly_payment?: number
  cached_rate_used?: number
}

export async function getScenarios(userId: number): Promise<Scenario[]> {
  const { data } = await api.get(`/api/v1/scenarios/user/${userId}`)
  return data
}

export async function createScenario(userId: number, payload: ScenarioPayload): Promise<Scenario> {
  const { data } = await api.post(`/api/v1/scenarios/user/${userId}`, payload)
  return data
}

export async function updateScenario(scenarioId: number, payload: Partial<ScenarioPayload>): Promise<Scenario> {
  const { data } = await api.put(`/api/v1/scenarios/${scenarioId}`, payload)
  return data
}

export async function deleteScenario(scenarioId: number): Promise<void> {
  await api.delete(`/api/v1/scenarios/${scenarioId}`)
}

export async function getReadiness(payload: ReadinessRequest): Promise<ReadinessResult> {
  const { data } = await api.post<ReadinessResult>('/api/v1/readiness', payload)
  return data
}

export async function setTargetZip(userId: number, targetZip: string | null): Promise<void> {
  await api.patch(`/api/v1/auth/target-zip/${userId}`, { target_zip: targetZip })
}

export async function getNearestZip(lat: number, lng: number): Promise<{
  zip_code: string; lat: number; lng: number; city: string | null; state_code: string | null
} | null> {
  try {
    const { data } = await api.get('/api/v1/zip/nearest', { params: { lat, lng } })
    return data
  } catch {
    return null
  }
}

export async function lookupZip(zip: string): Promise<{
  zip_code: string; lat: number; lng: number; city: string | null; state_code: string | null; state_name: string | null
}> {
  const { data } = await api.get(`/api/v1/zip/lookup`, { params: { zip } })
  return data
}

export async function getZipForecast(zip: string): Promise<{
  zip_code: string; city: string | null; state: string | null; metro: string | null
  current_median_value: number; as_of: string
  trend_3m_pct: number | null; trend_6m_pct: number | null; trend_12m_pct: number | null
  direction: string; data_points: number
}> {
  const { data } = await api.get(`/api/v1/zip/forecast`, { params: { zip } })
  return data
}

export async function compareNowVsWait(payload: {
  annual_income: number
  monthly_debt: number
  credit_score: number
  down_payment: number
  savings: number
  zip_code?: string
  loan_type?: string
  monthly_savings: number
  wait_months?: number
}) {
  const { data } = await api.post('/api/v1/compare/now-vs-wait', payload)
  return data
}

export async function getRentalAffordability(payload: {
  annual_income: number
  savings: number
  monthly_debt_car?: number
  monthly_debt_student?: number
  monthly_debt_credit?: number
  monthly_debt_other?: number
  credit_score?: number
  zip_code?: string
}): Promise<RentalAffordability> {
  const { data } = await api.post('/api/v1/rental-affordability', payload)
  return data
}
