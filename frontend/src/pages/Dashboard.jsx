import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/LoadingError'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const [signals, setSignals] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.signals().then(setSignals).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!signals) return <LoadingState />

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Watchlist</h1>
      <p className="mt-1 text-sm text-slate-500">
        All 30 KMI-30 companies, ranked by signal score. This is not financial advice — see each company's
        entry/target range and risk notes before acting.
      </p>

      <div className="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <Th>Ticker</Th>
              <Th>Status</Th>
              <Th>Score</Th>
              <Th>Price</Th>
              <Th>Why</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {signals.map((s) => (
              <tr key={s.ticker} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3">
                  <Link to={`/company/${s.ticker}`} className="font-medium text-indigo-600 hover:underline">
                    {s.ticker}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge status={s.status} />
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{s.score} / 3</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {s.current_price !== null ? s.current_price : '—'}
                </td>
                <td className="px-4 py-3 text-sm text-slate-500">
                  {Object.values(s.triggers).filter(Boolean).length
                    ? Object.values(s.triggers).find(Boolean)
                    : 'No triggers fired'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Th({ children }) {
  return <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{children}</th>
}
