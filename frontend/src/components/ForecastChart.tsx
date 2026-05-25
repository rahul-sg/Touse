import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import type { ForecastPoint } from '../types'
import styles from './ForecastChart.module.css'

interface Props {
  forecast: ForecastPoint[]
  currentPrice: number | null
}

function fmtPrice(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  return `$${Math.round(n / 1000)}K`
}

function fmtMonth(m: string) {
  const [year, month] = m.split('-')
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-US', {
    month: 'short',
    year: '2-digit',
  })
}

// Recharts passes tooltip props with a loose shape; this is the slim subset we need.
interface TooltipPayloadItem {
  dataKey: string
  value: number
}
interface ChartTooltipProps {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string
}

// Custom tooltip
function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length || !label) return null
  const price = payload.find((p) => p.dataKey === 'price')?.value
  const lower = payload.find((p) => p.dataKey === 'lower')?.value
  const upper = payload.find((p) => p.dataKey === 'upper')?.value
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipMonth}>{fmtMonth(label)}</p>
      {price != null && <p className={styles.tooltipPrice}>{fmtPrice(price)}</p>}
      {lower != null && upper != null && (
        <p className={styles.tooltipRange}>
          Range: {fmtPrice(lower)} – {fmtPrice(upper)}
        </p>
      )}
    </div>
  )
}

export default function ForecastChart({ forecast, currentPrice }: Props) {
  if (!forecast.length) {
    return (
      <div className={styles.empty}>
        <p>Forecast model not yet trained for this metro.</p>
        <p className={styles.emptyHint}>
          Run <code>python3 -m app.ml.train_prophet --all</code> after the Zillow ETL loads data.
        </p>
      </div>
    )
  }

  // Build chart data — band uses [lower, upper] area trick
  const data = forecast.map((p) => ({
    month: p.month,
    price: p.price,
    band: [p.lower, p.upper] as [number, number],
    lower: p.lower,
    upper: p.upper,
  }))

  const allPrices = forecast.flatMap((p) => [p.lower, p.upper, p.price])
  const yMin = Math.floor(Math.min(...allPrices) * 0.97 / 10000) * 10000
  const yMax = Math.ceil(Math.max(...allPrices) * 1.03 / 10000) * 10000

  return (
    <div className={styles.wrap}>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2DDD8" vertical={false} />

          <XAxis
            dataKey="month"
            tickFormatter={fmtMonth}
            tick={{ fontSize: 11, fill: '#9C9490', fontFamily: 'DM Sans, sans-serif' }}
            tickLine={false}
            axisLine={false}
          />

          <YAxis
            tickFormatter={fmtPrice}
            tick={{ fontSize: 11, fill: '#9C9490', fontFamily: 'DM Sans, sans-serif' }}
            tickLine={false}
            axisLine={false}
            domain={[yMin, yMax]}
            width={64}
          />

          <Tooltip content={<ChartTooltip />} />

          <Legend
            formatter={(value) =>
              value === 'price'
                ? 'Forecast'
                : value === 'band'
                ? '80% Confidence Range'
                : value
            }
            wrapperStyle={{ fontSize: 12 }}
          />

          {/* Confidence band */}
          <Area
            dataKey="band"
            stroke="none"
            fill="#1C3A2F"
            fillOpacity={0.08}
            name="band"
            legendType="rect"
            activeDot={false}
          />

          {/* Forecast line */}
          <Line
            dataKey="price"
            stroke="#B5935A"
            strokeWidth={2.5}
            dot={false}
            name="price"
            legendType="line"
          />

          {currentPrice && (
            <ReferenceLine
              y={currentPrice}
              stroke="#9C9490"
              strokeDasharray="4 4"
              label={{
                value: `Now: ${fmtPrice(currentPrice)}`,
                position: 'insideTopRight',
                fontSize: 11,
                fill: '#9C9490',
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
