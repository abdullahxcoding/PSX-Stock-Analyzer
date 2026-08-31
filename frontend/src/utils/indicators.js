// Plain rolling-mean SMA, same transparent formula as the backend's
// technical_service.compute_sma — run here over the full series so the
// chart can draw a line, since /api/technicals only returns the latest
// single value.
export function computeSmaSeries(closes, window) {
  return closes.map((_, i) => {
    if (i < window - 1) return null
    const slice = closes.slice(i - window + 1, i + 1)
    const sum = slice.reduce((acc, v) => acc + v, 0)
    return sum / window
  })
}
