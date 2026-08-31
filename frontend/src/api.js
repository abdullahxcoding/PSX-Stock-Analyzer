const BASE_URL = import.meta.env.VITE_API_BASE_URL

async function get(path) {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${response.status}`)
  }
  return response.json()
}

export const api = {
  companies: () => get('/api/companies'),
  prices: (ticker, limit = 300) => get(`/api/prices/${ticker}?limit=${limit}`),
  fundamentals: (ticker) => get(`/api/fundamentals/${ticker}`),
  fundamentalsComparison: (ticker) => get(`/api/fundamentals/${ticker}/comparison`),
  technicals: (ticker) => get(`/api/technicals/${ticker}`),
  news: (ticker) => get(`/api/news/${ticker}`),
  macro: (ticker) => get(`/api/macro/${ticker}`),
  signals: () => get('/api/signals'),
  signal: (ticker) => get(`/api/signals/${ticker}`),
}
