export function LoadingState() {
  return <p className="text-sm text-slate-400">Loading…</p>
}

export function ErrorState({ message }) {
  return (
    <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-inset ring-red-600/20">
      Failed to load: {message}
    </div>
  )
}
