import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/LoadingError'
import StatusBadge from '../components/StatusBadge'

const SHARIAH_OPTIONS = ['all', 'compliant', 'non_compliant', 'under_review', 'unknown']
const STATUS_OPTIONS = ['all', 'watch', 'consider', 'none']
const SORT_OPTIONS = { score: 'Score', price: 'Price' }

export default function Companies() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  const [shariahFilter, setShariahFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('score')

  useEffect(() => {
    Promise.all([api.companies(), api.signals()])
      .then(([companies, signals]) => {
        const signalByTicker = Object.fromEntries(signals.map((s) => [s.ticker, s]))
        setRows(companies.map((c) => ({ ...c, signal: signalByTicker[c.ticker] })))
      })
      .catch((e) => setError(e.message))
  }, [])

  const filtered = useMemo(() => {
    if (!rows) return []
    return rows
      .filter((r) => shariahFilter === 'all' || r.shariah_compliance_status === shariahFilter)
      .filter((r) => statusFilter === 'all' || r.signal?.status === statusFilter)
      .sort((a, b) => {
        if (sortBy === 'score') return (b.signal?.score ?? -1) - (a.signal?.score ?? -1)
        return (b.signal?.current_price ?? -Infinity) - (a.signal?.current_price ?? -Infinity)
      })
  }, [rows, shariahFilter, statusFilter, sortBy])

  if (error) return <ErrorState message={error} />
  if (!rows) return <LoadingState />

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Companies</h1>
      <p className="mt-1 text-sm text-slate-500">
        A limited screener — sortable/filterable by Shariah compliance status, signal status, and price. Sector
        and market-cap/valuation filters aren't available yet (that data hasn't been sourced).
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        <Select label="Shariah status" value={shariahFilter} onChange={setShariahFilter} options={SHARIAH_OPTIONS} />
        <Select label="Signal status" value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
        <Select label="Sort by" value={sortBy} onChange={setSortBy} options={Object.keys(SORT_OPTIONS)} labels={SORT_OPTIONS} />
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <Th>Ticker</Th>
              <Th>Name</Th>
              <Th>Shariah</Th>
              <Th>Signal</Th>
              <Th>Price</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((r) => (
              <tr key={r.ticker} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3">
                  <Link to={`/company/${r.ticker}`} className="font-medium text-indigo-600 hover:underline">
                    {r.ticker}
                  </Link>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">{r.name}</td>
                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge status={r.shariah_compliance_status} />
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  {r.signal ? <StatusBadge status={r.signal.status} /> : '—'}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {r.signal?.current_price ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <p className="px-4 py-6 text-center text-sm text-slate-400">No companies match these filters.</p>}
      </div>
    </div>
  )
}

function Select({ label, value, onChange, options, labels }) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-600">
      {label}
      <select
        className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {labels?.[opt] ?? opt}
          </option>
        ))}
      </select>
    </label>
  )
}

function Th({ children }) {
  return <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{children}</th>
}
