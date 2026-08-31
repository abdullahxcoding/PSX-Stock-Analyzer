import { useEffect, useRef } from 'react'

// Re-runs `callback` every `delayMs`, without the classic setInterval
// stale-closure trap (the ref always points at the latest callback).
export function useInterval(callback, delayMs) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    if (delayMs === null) return
    const id = setInterval(() => savedCallback.current(), delayMs)
    return () => clearInterval(id)
  }, [delayMs])
}
