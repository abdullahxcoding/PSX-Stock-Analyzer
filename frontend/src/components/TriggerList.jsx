const LABELS = {
  fundamental: 'Fundamental',
  technical: 'Technical',
  news: 'News',
}

export default function TriggerList({ triggers, riskCaution }) {
  return (
    <div className="space-y-3">
      {Object.entries(triggers).map(([key, reason]) => (
        <div key={key} className="flex items-start gap-3">
          <span
            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              reason ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'
            }`}
          >
            {reason ? '✓' : '–'}
          </span>
          <div>
            <p className="text-sm font-medium text-slate-700">{LABELS[key] || key}</p>
            <p className="text-sm text-slate-500">{reason || 'Not triggered — insufficient data or below threshold'}</p>
          </div>
        </div>
      ))}
      {riskCaution && (
        <div className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 ring-1 ring-inset ring-amber-600/20">
          ⚠ {riskCaution}
        </div>
      )}
    </div>
  )
}
