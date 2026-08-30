def pct_change(current: float | None, previous: float | None) -> float | None:
    """Percentage change from `previous` to `current`. None if either value
    is missing or previous is zero — never fabricate a comparison."""
    if current is None or previous is None or previous == 0:
        return None
    return round((float(current) - float(previous)) / abs(float(previous)) * 100, 2)
