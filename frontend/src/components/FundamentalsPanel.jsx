function fmtNumber(n) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function ComparisonRow({ label, comparison }) {
  if (!comparison) return null
  const metric = comparison.profit_after_tax
  const positive = metric.pct_change !== null && metric.pct_change >= 0
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">
        {label} ({comparison.previous_period} → {comparison.current_period})
      </span>
      <span className={`font-medium ${positive ? 'text-emerald-600' : 'text-red-600'}`}>
        {metric.pct_change === null ? '—' : `${metric.pct_change > 0 ? '+' : ''}${metric.pct_change}%`}
      </span>
    </div>
  )
}

export default function FundamentalsPanel({ fundamentals, comparison }) {
  const latestAnnual = fundamentals.find((f) => f.period_type === 'annual')
  const latestQuarterly = fundamentals.find((f) => f.period_type === 'quarterly')

  return (
    <div className="space-y-4">
      {latestAnnual && (
        <div className="grid grid-cols-3 gap-3">
          <Stat label={`Sales (FY${latestAnnual.fiscal_year})`} value={fmtNumber(latestAnnual.sales)} suffix="'000" />
          <Stat label="Profit after Tax" value={fmtNumber(latestAnnual.profit_after_tax)} suffix="'000" />
          <Stat label="EPS" value={fmtNumber(latestAnnual.eps)} />
        </div>
      )}
      {latestQuarterly && (
        <p className="text-xs text-slate-400">
          Latest quarter: Q{latestQuarterly.fiscal_quarter} {latestQuarterly.fiscal_year} — profit after tax{' '}
          {fmtNumber(latestQuarterly.profit_after_tax)}
        </p>
      )}
      <div className="space-y-1 border-t border-slate-100 pt-3">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Profit growth</p>
        <ComparisonRow label="QoQ" comparison={comparison?.qoq} />
        <ComparisonRow label="YoY" comparison={comparison?.yoy} />
        {!comparison?.qoq && !comparison?.yoy && <p className="text-sm text-slate-400">Not enough data yet</p>}
      </div>
    </div>
  )
}

function Stat({ label, value, suffix }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-slate-800">
        {value} {suffix && <span className="text-xs font-normal text-slate-400">{suffix}</span>}
      </p>
    </div>
  )
}
