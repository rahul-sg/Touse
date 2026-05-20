export interface AffordabilityResult {
  max_price: number
  max_loan: number
  monthly_payment: number
  rate_used: number
  down_payment: number
  buying_power_change_per_half_point: number
}

export interface ForecastPoint {
  month: string
  price: number
  lower: number
  upper: number
}

export interface TopDrivers {
  strongest_growth_periods: string[]
  strongest_decline_periods: string[]
}

export interface MetroForecast {
  metro_id: string
  model_version: string | null
  trained_at: string | null
  current_median_price: number | null
  trend_3m: number | null
  trend_12m: number | null
  forecast_12m: ForecastPoint[]
  top_drivers: TopDrivers | Record<string, never>
  note?: string
}

export interface Listing {
  id: string
  address: string
  price: number
  beds: number
  baths: number
  lat: number
  lng: number
  listing_url: string
}

export interface MarketIndicators {
  metro_id: string
  mortgage_rate: number | null
  unemployment: number | null
  cpi_yoy: number | null
  gdp_growth: number | null
  affordability_index: number | null
  policy_notes: string[]
}

export interface Region {
  metro_id: string
  name: string
  state: string
  zip_codes: string[]
}

export interface UserProfile {
  user_id: number
  first_name: string
  last_name: string
  email: string
  username: string
  annual_income: number | null
  savings: number | null
  down_payment: number | null
  credit_score: number | null
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string | null
  target_zip: string | null
}

export interface ReadinessResult {
  score: number
  components: {
    dti_pts: number
    dp_pts: number
    credit_pts: number
    cushion_pts: number
  }
  dti_ratio_pct: number
  dti_ceiling_pct: number
  dp_pct: number
  cushion_months: number
  credit_label: string
  rate_used: number
  target_price: number
  actions: string[]
}

export interface Scenario {
  id: number
  user_id: number
  name: string
  scenario_type: 'buy' | 'rent'
  annual_income: number | null
  savings: number | null
  down_payment: number | null
  credit_score: number | null
  monthly_debt_car: number
  monthly_debt_student: number
  monthly_debt_credit: number
  monthly_debt_other: number
  zip_code: string | null
  cached_max_price: number | null
  cached_monthly_payment: number | null
  cached_rate_used: number | null
  is_active: boolean
  created_at: string
}

export interface RentalAffordability {
  max_monthly_rent: number
  recommended_monthly_rent: number
  move_in_cost_estimate: number
  months_of_rent_in_savings: number
  savings_adequate_for_move_in: boolean
  annual_rent_cost: number
  existing_dti_pct: number
  credit_label: string
  total_monthly_debt: number
  gross_monthly_income: number
}
