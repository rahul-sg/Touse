import axios from 'axios'
import type { Scenario, RentalAffordability, ReadinessResult } from '../types'

// Must match STORAGE_KEY in AuthContext.tsx
const AUTH_STORAGE_KEY = 'touse_auth'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Attach the JWT (stored by AuthContext) as a Bearer token on every request.
api.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    const token = raw ? JSON.parse(raw)?.access_token : null
    if (token) config.headers.Authorization = `Bearer ${token}`
  } catch {
    // malformed storage — proceed unauthenticated
  }
  return config
})

// On 401 (expired/invalid session) clear the stored auth and bounce to login.
api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

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
  email_verified: boolean
}

export interface ReadinessRequest {
  scenario_type?: 'buy' | 'rent'
  annual_income: number
  savings?: number
  down_payment?: number
  credit_score?: number
  monthly_debt_car?: number
  monthly_debt_student?: number
  monthly_debt_credit?: number
  monthly_debt_other?: number
  cached_max_price?: number
  cached_monthly_payment?: number
  rate_used?: number
  liquid_savings?: number
  target_zip?: string
}

// Re-export so callers can import ReadinessResult from either api.ts or types/index.ts
export type { ReadinessResult }

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/v1/auth/register', payload)
  return data
}

/** `identifier` may be an email address or a username. */
export async function loginUser(identifier: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/v1/auth/login', { identifier, password })
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
  home_type?: string  // 'all' | 'single_family' | 'condo'
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

export async function updateScenario(publicId: string, payload: Partial<ScenarioPayload>): Promise<Scenario> {
  const { data } = await api.put(`/api/v1/scenarios/${publicId}`, payload)
  return data
}

export async function deleteScenario(publicId: string): Promise<void> {
  await api.delete(`/api/v1/scenarios/${publicId}`)
}

/** Mark a scenario as the user's primary (drives the dashboard headline + map default). */
export async function setPrimaryScenario(publicId: string): Promise<void> {
  await api.patch(`/api/v1/scenarios/${publicId}/primary`)
}

export async function getReadiness(payload: ReadinessRequest): Promise<ReadinessResult> {
  const { data } = await api.post<ReadinessResult>('/api/v1/readiness', payload)
  return data
}

export async function setTargetZip(userId: number, targetZip: string | null): Promise<void> {
  await api.patch(`/api/v1/auth/target-zip/${userId}`, { target_zip: targetZip })
}

export interface AccountInfo {
  user_id: number
  first_name: string
  last_name: string
  email: string
  username: string
}

export async function updateAccount(
  userId: number,
  payload: { first_name?: string; last_name?: string; email?: string },
): Promise<AccountInfo> {
  const { data } = await api.patch<AccountInfo>(`/api/v1/auth/account/${userId}`, payload)
  return data
}

export async function changePassword(
  userId: number,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await api.post(`/api/v1/auth/change-password/${userId}`, {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function submitContact(payload: {
  name: string
  email: string
  message: string
}): Promise<void> {
  await api.post('/api/v1/contact', payload)
}

export async function verifyEmail(token: string): Promise<void> {
  await api.post('/api/v1/auth/verify-email', { token })
}

export async function resendVerification(userId: number): Promise<void> {
  await api.post(`/api/v1/auth/resend-verification/${userId}`)
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

export async function getZipForecast(zip: string, homeType: string = 'all'): Promise<{
  zip_code: string; city: string | null; state: string | null; metro: string | null
  current_median_value: number; as_of: string
  trend_3m_pct: number | null; trend_6m_pct: number | null; trend_12m_pct: number | null
  direction: string; data_points: number
}> {
  const { data } = await api.get(`/api/v1/zip/forecast`, { params: { zip, home_type: homeType } })
  return data
}

export interface ZipProjection {
  zip_code: string
  home_type: string
  model_version: string
  trained_at: string
  current_value: number
  forecast_12m_pct: number | null
  data_points: number
  forecast_12m: { month: string; price: number; lower: number; upper: number }[]
}

/** 12-month Prophet projection for a (ZIP, home_type) — trains on demand on first request. */
export async function getZipProjection(zip: string, homeType: string = 'all'): Promise<ZipProjection> {
  const { data } = await api.get<ZipProjection>('/api/v1/zip/projection', {
    params: { zip, home_type: homeType },
  })
  return data
}

export interface MarketContext {
  zip_code: string
  state_code: string | null
  mortgage_rate_30y: number | null
  mortgage_rate_as_of: string | null
  cpi_yoy_pct: number | null
  unemployment_pct: number | null
  fed_funds_rate: number | null
  state_gdp_growth_pct: number | null
  state_gdp_year: number | null
}

/** National + state-level economic indicators relevant to a ZIP's market. */
export async function getMarketContext(zip: string): Promise<MarketContext> {
  const { data } = await api.get<MarketContext>('/api/v1/zip/market-context', { params: { zip } })
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

// ── Methodology ──────────────────────────────────────────────────────────────

export interface MethodologySummary {
  model: {
    version: string
    trained_at: string
    panel_rows: number
    train_rows: number
    feature_count: number
    zips_predicted: number
    train_seconds: number
    backtest_mape_all: number | null
    backtest_bias_all: number | null
    backtest_per_type: Record<string, { n: number; mape: number; smape: number; bias: number }> | null
    notes: string | null
  } | null
  coverage: {
    by_home_type: Record<string, number>
    total_predictions: number
    latest_price_month: string | null
  }
  features: { group: string; items: string[] }[]
  pipeline: { stage_1: string; stage_2: string; fallback: string }
}

export async function getMethodologySummary(): Promise<MethodologySummary> {
  const { data } = await api.get('/api/v1/methodology/summary')
  return data
}

// ── Per-ZIP realized forecast accuracy ───────────────────────────────────────

export interface ZipForecastAccuracy {
  zip_code: string
  home_type: string
  samples: number
  mape: number | null
  bias: number | null
  last_realized_at: string | null
}

export async function getZipForecastAccuracy(
  zip: string,
  homeType: string = 'all'
): Promise<ZipForecastAccuracy> {
  const { data } = await api.get('/api/v1/zip/forecast-accuracy', {
    params: { zip, home_type: homeType },
  })
  return data
}
