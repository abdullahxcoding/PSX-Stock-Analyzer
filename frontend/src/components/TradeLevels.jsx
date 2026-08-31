function Row({ label, value, tone }) {
  const toneClass = { danger: 'text-red-600', good: 'text-emerald-600' }[tone] || 'text-slate-700'
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className={`font-medium ${toneClass}`}>{value ?? '—'}</span>
    </div>
  )
}

export default function TradeLevels({ signal }) {
  const hasLevels = signal?.entry_zone && signal?.targets && signal?.stop_loss !== null

  if (!hasLevels) {
    return <p className="text-sm text-slate-400">Not enough price history to compute trade levels yet.</p>
  }

  const [target1, target2, target3] = signal.targets

  return (
    <div className="space-y-1.5">
      <Row label="Support" value={signal.entry_zone.low} />
      <Row label="Resistance" value={target1} />
      <div className="my-1 border-t border-slate-100" />
      <Row label="Target 1" value={target1} tone="good" />
      <Row label="Target 2" value={target2} tone="good" />
      <Row label="Target 3" value={target3} tone="good" />
      <Row label="Stop loss" value={signal.stop_loss} tone="danger" />
      <p className="pt-2 text-xs text-slate-400">
        Targets are a measured-move projection: the support-resistance range repeated above resistance — a
        standard charting heuristic, not a prediction. Stop loss sits just below support with a buffer. {signal.risk_note}
      </p>
    </div>
  )
}
