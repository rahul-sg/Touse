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
