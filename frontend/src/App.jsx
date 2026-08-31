import { NavLink, Route, Routes } from 'react-router-dom'
import Companies from './pages/Companies'
import CompanyDetail from './pages/CompanyDetail'
import Dashboard from './pages/Dashboard'

const navLinkClass = ({ isActive }) =>
  `px-3 py-2 text-sm font-medium rounded-md ${isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <span className="text-lg font-bold text-slate-900">PSX Shariah Analyzer</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Watchlist
            </NavLink>
            <NavLink to="/companies" className={navLinkClass}>
              Companies
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/company/:ticker" element={<CompanyDetail />} />
        </Routes>
      </main>
    </div>
  )
}
