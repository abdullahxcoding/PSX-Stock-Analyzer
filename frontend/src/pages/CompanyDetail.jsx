import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, LIVE_POLL_INTERVAL_MS } from '../api'
import { ErrorState, LoadingState } from '../components/LoadingError'
import LiveDot from '../components/LiveDot'
import StatusBadge from '../components/StatusBadge'
import FundamentalsPanel from '../components/FundamentalsPanel'
import MacroContext from '../components/MacroContext'
import NewsList from '../components/NewsList'
import PriceChart from '../components/PriceChart'
import TradeLevels from '../components/TradeLevels'
import TriggerList from '../components/TriggerList'
import { useInterval } from '../hooks/useInterval'

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

  // Live refresh: only the fast-changing pieces (price series + signal, which
  // carries the current price and re-derived trade levels). Fundamentals,
  // comparison, and news are daily-cadence backend data — re-fetching them
  // every 15s would just be wasted requests for data that hasn't changed.
  const refreshLive = useCallback(() => {
    Promise.all([api.prices(ticker), api.signal(ticker)])
      .then(([prices, signal]) => setData((prev) => (prev ? { ...prev, prices, signal } : prev)))
      .catch(() => {}) // a transient live-refresh failure shouldn't blow away what's on screen
  }, [ticker])

  useInterval(refreshLive, data ? LIVE_POLL_INTERVAL_MS : null)

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
        <LiveDot />
      </div>

      <Section title="Price & moving averages">
        <PriceChart prices={prices} levels={levelsFromSignal(signal)} />
      </Section>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Section title="Signal reasoning">
          <TriggerList triggers={signal.triggers} riskCaution={signal.risk_caution} />
        </Section>

        <Section title="Fundamentals">
          <FundamentalsPanel fundamentals={fundamentals} comparison={comparison} />
        </Section>

        <Section title="Trade levels">
          <TradeLevels signal={signal} />
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

// Support/resistance aren't separately exposed on the signal payload — they're
// recoverable from entry_zone.low (support) and target_range.high (resistance,
// == targets[0]), which the backend already derives from the same numbers.
function levelsFromSignal(signal) {
  if (!signal?.entry_zone || !signal?.targets) return null
  return {
    support: signal.entry_zone.low,
    resistance: signal.targets[0],
    target2: signal.targets[1],
    target3: signal.targets[2],
    stopLoss: signal.stop_loss,
  }
}

function Section({ title, children }) {
  return (
    <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      <div className="mt-3">{children}</div>
    </div>
  )
}
