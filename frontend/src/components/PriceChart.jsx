import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { computeSmaSeries } from '../utils/indicators'

// Validated categorical palette (dataviz skill, references/palette.md) —
// slots 1/2/3 (blue/orange/aqua) clear every adjacent + all-pairs CVD gate.
const COLORS = { price: '#2a78d6', sma50: '#eb6834', sma200: '#1baf7a' }
// Status palette (same skill) — reserved for good/critical meaning, never
// reused as a 4th/5th categorical series, and kept visually recessive
// (dashed, thin) so reference levels read as chart chrome, not data series.
const STATUS = { good: '#0ca30c', critical: '#d03b3b', neutral: '#898781' }

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: '2-digit' })
}

export default function PriceChart({ prices, levels }) {
  // prices: EOD rows, most-recent-first from the API — reverse to ascending for charting.
  const ascending = [...prices].filter((p) => p.interval_type === 'eod').reverse()
  const closes = ascending.map((p) => Number(p.close))
  const sma50 = computeSmaSeries(closes, 50)
  const sma200 = computeSmaSeries(closes, 200)

  const data = ascending.map((p, i) => ({
    date: p.timestamp,
    price: closes[i],
    sma50: sma50[i],
    sma200: sma200[i],
  }))

  if (data.length < 2) {
    return <p className="text-sm text-slate-400">Not enough price history to chart yet.</p>
  }

  // Reference levels rendered as constant-value series (not <ReferenceLine>
  // + inline label) — by construction they cluster close together near
  // current price, so per-line text labels collide at chart scale
  // regardless of position tuning. A flat dashed line + real legend entry
  // (same auto-registration mechanism as Price/SMA below) never collides;
  // exact values are also in the Trade Levels panel underneath the chart.
  if (levels) {
    for (const row of data) {
      if (levels.resistance != null) row.resistance = levels.resistance
      if (levels.target2 != null) row.target2 = levels.target2
      if (levels.target3 != null) row.target3 = levels.target3
      if (levels.stopLoss != null) row.stopLoss = levels.stopLoss
    }
  }

  // Widen the y-axis so the highest target and lowest stop-loss are never
  // clipped out of view even if they sit beyond the plotted price history.
  const levelValues = levels ? Object.values(levels).filter((v) => v !== null && v !== undefined) : []
  const yDomain = levelValues.length
    ? [Math.min(...closes, ...levelValues), Math.max(...closes, ...levelValues)]
    : ['auto', 'auto']

  const NAMES = {
    price: 'Price', sma50: 'SMA 50', sma200: 'SMA 200',
    resistance: 'Resistance', target2: 'Target 2', target3: 'Target 3', stopLoss: 'Stop loss',
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e1e0d9" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={fmtDate}
          stroke="#898781"
          fontSize={12}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          domain={yDomain}
          stroke="#898781"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={56}
        />
        <Tooltip
          labelFormatter={fmtDate}
          formatter={(value, name) => [value?.toFixed(2), NAMES[name] || name]}
          contentStyle={{ fontSize: 13, borderRadius: 8, border: '1px solid #e1e0d9' }}
        />
        <Legend formatter={(value) => NAMES[value] || value} wrapperStyle={{ fontSize: 12 }} />

        <Line type="monotone" dataKey="price" stroke={COLORS.price} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="sma50" stroke={COLORS.sma50} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="sma200" stroke={COLORS.sma200} dot={false} strokeWidth={2} />

        {levels?.resistance != null && (
          <Line dataKey="resistance" stroke={STATUS.neutral} strokeDasharray="4 4" strokeWidth={1.5} dot={false} />
        )}
        {levels?.target2 != null && (
          <Line dataKey="target2" stroke={STATUS.good} strokeDasharray="4 4" strokeWidth={1.5} dot={false} />
        )}
        {levels?.target3 != null && (
          <Line dataKey="target3" stroke={STATUS.good} strokeDasharray="4 4" strokeWidth={1.5} dot={false} />
        )}
        {levels?.stopLoss != null && (
          <Line dataKey="stopLoss" stroke={STATUS.critical} strokeDasharray="4 4" strokeWidth={1.5} dot={false} />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
