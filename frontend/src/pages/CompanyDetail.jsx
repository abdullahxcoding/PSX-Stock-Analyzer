import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, LoadingState } from '../components/LoadingError'
import StatusBadge from '../components/StatusBadge'
import FundamentalsPanel from '../components/FundamentalsPanel'
import MacroContext from '../components/MacroContext'
import NewsList from '../components/NewsList'
import PriceChart from '../components/PriceChart'
import TriggerList from '../components/TriggerList'

export default function CompanyDetail() {
  const { ticker } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setData(null)
    setError(null)
    Promise.all([
      api.companies(),
      api.prices(ticker),
      api.fundamentals(ticker),
      api.fundamentalsComparison(ticker),
      api.news(ticker),
      api.signal(ticker),
    ])
      .then(([companies, prices, fundamentals, comparison, news, signal]) => {
        const company = companies.find((c) => c.ticker === ticker)
        setData({ company, prices, fundamentals, comparison, news, signal })
      })
      .catch((e) => setError(e.message))
  }, [ticker])

  if (error) return <ErrorState message={error} />
  if (!data) return <LoadingState />

  const { company, prices, fundamentals, comparison, news, signal } = data

  return (
    <div>
      <Link to="/" className="text-sm text-indigo-600 hover:underline">
        ← Back to watchlist
      </Link>

      <div className="mt-2 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">{company?.name ?? ticker}</h1>
        <span className="text-slate-400">{ticker}</span>
        {company && <StatusBadge status={company.shariah_compliance_status} />}
        {signal && <StatusBadge status={signal.status} />}
        {signal?.current_price !== null && signal?.current_price !== undefined && (
          <span className="text-lg font-semibold text-slate-700">{signal.current_price}</span>
        )}
      </div>

      <Section title="Price & moving averages">
        <PriceChart prices={prices} />
      </Section>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Section title="Signal reasoning">
          <TriggerList triggers={signal.triggers} riskCaution={signal.risk_caution} />
        </Section>

        <Section title="Fundamentals">
          <FundamentalsPanel fundamentals={fundamentals} comparison={comparison} />
        </Section>

        <Section title="Entry zone / target range">
          {signal.entry_zone && signal.target_range ? (
            <div className="space-y-2 text-sm">
              <Range label="Entry zone" range={signal.entry_zone} />
              <Range label="Target range" range={signal.target_range} />
              <p className="pt-2 text-xs text-slate-400">{signal.risk_note}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Not enough price history to compute a range yet.</p>
          )}
        </Section>

        <Section title="Macro context">
          <MacroContext sentences={signal.macro_context} />
        </Section>
      </div>

      <Section title="Recent news & announcements">
        <NewsList items={news} />
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      <div className="mt-3">{children}</div>
    </div>
  )
}

function Range({ label, range }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-700">
        {range.low} – {range.high}
      </span>
    </div>
  )
}
