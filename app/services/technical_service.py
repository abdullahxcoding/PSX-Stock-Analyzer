"""Technical indicator computation: SMA, RSI, volume MA, support/resistance.

All computation functions are pure (plain lists in, values out) so they're
unit-testable without a DB. Only get_technicals() touches the database.

Deliberately plain Python, no pandas — the formulas involved (SMA, Wilder's
RSI, rolling min/max) are simple enough, and this box already hit a native-
wheel compatibility issue with lxml on Python 3.14 during Phase 1.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PriceOHLCV


def compute_sma(closes: list[float], window: int) -> float | None:
    """Simple moving average of the most recent `window` closes.
    None if fewer than `window` points are available — never fabricate."""
    if len(closes) < window or window <= 0:
        return None
    return round(sum(closes[-window:]) / window, 4)


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's smoothing RSI. None if fewer than `period` + 1 points available."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_volume_ma(volumes: list[int], window: int = 20) -> float | None:
    values = [v for v in volumes if v is not None]
    if len(values) < window or window <= 0:
        return None
    return round(sum(values[-window:]) / window, 2)


def _find_swing_pivots(closes: list[float], pivot_window: int) -> tuple[list[float], list[float]]:
    """A close is a swing high/low if it's the max/min within ±pivot_window
    trading days. Returns (swing_highs, swing_lows)."""
    swing_highs, swing_lows = [], []
    n = len(closes)
    for i in range(pivot_window, n - pivot_window):
        window = closes[i - pivot_window : i + pivot_window + 1]
        if closes[i] == max(window):
            swing_highs.append(closes[i])
        if closes[i] == min(window):
            swing_lows.append(closes[i])
    return swing_highs, swing_lows


def compute_support_resistance(
    closes: list[float], lookback: int = 90, pivot_window: int = 5
) -> dict:
    """Support/resistance via local swing-pivot detection over the last
    `lookback` closes, falling back to plain rolling max/min if no pivots
    are found (e.g. too little data). Returns {"support": ..., "resistance": ...}."""
    if not closes:
        return {"support": None, "resistance": None}

    recent = closes[-lookback:] if len(closes) > lookback else closes
    current_price = closes[-1]

    swing_highs, swing_lows = _find_swing_pivots(recent, pivot_window)

    resistance_candidates = [p for p in swing_highs if p > current_price]
    support_candidates = [p for p in swing_lows if p < current_price]

    # Fall back to the window's plain rolling max/min when no swing pivot
    # was found on the relevant side (e.g. too little data, or a trending
    # series with no interior local extremum).
    resistance = min(resistance_candidates) if resistance_candidates else max(recent)
    support = max(support_candidates) if support_candidates else min(recent)

    return {"support": round(support, 4), "resistance": round(resistance, 4)}


def compute_price_levels(support: float | None, resistance: float | None) -> dict:
    """Measured-move projection — a standard, named technical-analysis
    heuristic, not a new prediction model: the support-resistance range is
    projected forward from resistance for two further targets; stop-loss
    sits just below support, offset by a quarter of that same range as a
    noise buffer. Not a guarantee — same caveat as support/resistance itself.
    None for all four if support/resistance aren't available."""
    if support is None or resistance is None:
        return {"target_1": None, "target_2": None, "target_3": None, "stop_loss": None}

    range_ = resistance - support
    return {
        "target_1": round(resistance, 4),
        "target_2": round(resistance + range_, 4),
        "target_3": round(resistance + 2 * range_, 4),
        "stop_loss": round(support - 0.25 * range_, 4),
    }


def get_technicals(session: Session, ticker: str) -> dict:
    rows = session.execute(
        select(PriceOHLCV.close, PriceOHLCV.volume)
        .where(PriceOHLCV.ticker == ticker, PriceOHLCV.interval_type == "eod")
        .order_by(PriceOHLCV.timestamp.asc())
    ).all()

    closes = [float(r.close) for r in rows]
    volumes = [int(r.volume) for r in rows if r.volume is not None]

    support_resistance = compute_support_resistance(closes) if closes else {"support": None, "resistance": None}
    price_levels = compute_price_levels(support_resistance["support"], support_resistance["resistance"])

    return {
        "current_price": closes[-1] if closes else None,
        "sma_20": compute_sma(closes, 20),
        "sma_50": compute_sma(closes, 50),
        "sma_200": compute_sma(closes, 200),
        "rsi_14": compute_rsi(closes, 14),
        "volume_ma_20": compute_volume_ma(volumes, 20),
        "support": support_resistance["support"],
        "resistance": support_resistance["resistance"],
        **price_levels,
    }
