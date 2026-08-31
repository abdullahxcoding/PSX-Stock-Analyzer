const STYLES = {
  watch: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
  consider: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  none: 'bg-slate-100 text-slate-600 ring-slate-500/20',
  compliant: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
  non_compliant: 'bg-red-100 text-red-800 ring-red-600/20',
  under_review: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  unknown: 'bg-slate-100 text-slate-600 ring-slate-500/20',
}

export default function StatusBadge({ status, children }) {
  const style = STYLES[status] || STYLES.none
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style}`}>
      {children ?? status}
    </span>
  )
}
