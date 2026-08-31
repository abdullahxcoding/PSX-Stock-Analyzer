function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function NewsList({ items }) {
  if (!items.length) {
    return <p className="text-sm text-slate-400">No recent announcements or news found.</p>
  }

  return (
    <ul className="divide-y divide-slate-100">
      {items.map((item, i) => (
        <li key={i} className="py-2">
          <div className="flex items-center justify-between gap-2">
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-slate-700 hover:text-indigo-600 hover:underline"
            >
              {item.title}
            </a>
            <span className="shrink-0 text-xs text-slate-400">{fmtDate(item.published_at)}</span>
          </div>
          <p className="text-xs text-slate-400">
            {item.source_type === 'psx_announcement' ? `PSX · ${item.category}` : item.source}
          </p>
        </li>
      ))}
    </ul>
  )
}
