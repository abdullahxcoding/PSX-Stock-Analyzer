from app.services.technical_service import (
    compute_price_levels,
    compute_rsi,
    compute_sma,
    compute_support_resistance,
    compute_volume_ma,
)


def test_sma_basic():
    closes = [10, 20, 30, 40, 50]
    assert compute_sma(closes, 5) == 30.0
    assert compute_sma(closes, 3) == 40.0  # last 3: 30,40,50 -> avg 40


def test_sma_insufficient_data_returns_none():
    assert compute_sma([1, 2, 3], 5) is None
    assert compute_sma([], 20) is None


def test_rsi_all_gains_is_100():
    closes = [float(i) for i in range(1, 20)]  # strictly increasing
    assert compute_rsi(closes, 14) == 100.0


def test_rsi_classic_worked_example():
    # Classic Wilder's RSI worked example (14-period), commonly cited reference
    # prices, expected RSI ~70.53 after the smoothing.
    closes = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
        46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
    ]
    rsi = compute_rsi(closes, 14)
    assert rsi is not None
    assert 69.0 < rsi < 72.0


def test_rsi_insufficient_data_returns_none():
    assert compute_rsi([1.0, 2.0, 3.0], 14) is None


def test_volume_ma_basic():
    volumes = [100, 200, 300, 400, 500]
    assert compute_volume_ma(volumes, 5) == 300.0


def test_volume_ma_insufficient_data_returns_none():
    assert compute_volume_ma([100, 200], 20) is None


def test_support_resistance_finds_swing_pivots():
    # Engineered: a clear swing low at index 5 (90) and swing high at index 10 (150),
    # with current price (last close) sitting between them.
    closes = [
        100, 105, 110, 100, 95, 90, 95, 100, 110, 130, 150, 140, 120, 115, 118,
    ]
    result = compute_support_resistance(closes, lookback=15, pivot_window=2)
    assert result["support"] is not None
    assert result["resistance"] is not None
    assert result["support"] < closes[-1] < result["resistance"]


def test_support_resistance_empty_returns_none():
    result = compute_support_resistance([])
    assert result == {"support": None, "resistance": None}


def test_support_resistance_falls_back_to_min_max_when_no_pivots():
    # Monotonically increasing -> no interior swing pivots exist.
    closes = [float(i) for i in range(1, 30)]
    result = compute_support_resistance(closes, lookback=30, pivot_window=5)
    assert result["support"] == min(closes)
    assert result["resistance"] == max(closes)


def test_price_levels_measured_move():
    result = compute_price_levels(support=90, resistance=110)
    assert result["target_1"] == 110
    assert result["target_2"] == 130
    assert result["target_3"] == 150
    assert result["stop_loss"] == 85


def test_price_levels_none_when_support_or_resistance_missing():
    assert compute_price_levels(None, 110) == {
        "target_1": None, "target_2": None, "target_3": None, "stop_loss": None,
    }
    assert compute_price_levels(90, None) == {
        "target_1": None, "target_2": None, "target_3": None, "stop_loss": None,
    }
