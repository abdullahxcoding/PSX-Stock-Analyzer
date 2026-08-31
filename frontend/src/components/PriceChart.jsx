import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { computeSmaSeries } from '../utils/indicators'

// Validated categorical palette (dataviz skill, references/palette.md) —
// slots 1/2/3 (blue/orange/aqua) clear every adjacent + all-pairs CVD gate.
const COLORS = { price: '#2a78d6', sma50: '#eb6834', sma200: '#1baf7a' }

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: '2-digit' })
}

export default function PriceChart({ prices }) {
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

  return (
    <ResponsiveContainer width="100%" height={320}>
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
          domain={['auto', 'auto']}
          stroke="#898781"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={56}
        />
        <Tooltip
          labelFormatter={fmtDate}
          formatter={(value, name) => [value?.toFixed(2), { price: 'Price', sma50: 'SMA 50', sma200: 'SMA 200' }[name]]}
          contentStyle={{ fontSize: 13, borderRadius: 8, border: '1px solid #e1e0d9' }}
        />
        <Legend
          formatter={(value) => ({ price: 'Price', sma50: 'SMA 50', sma200: 'SMA 200' }[value])}
          wrapperStyle={{ fontSize: 13 }}
        />
        <Line type="monotone" dataKey="price" stroke={COLORS.price} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="sma50" stroke={COLORS.sma50} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="sma200" stroke={COLORS.sma200} dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
