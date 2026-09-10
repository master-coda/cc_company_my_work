import numpy as np
import pandas as pd
from src.indicators import add_indicators


def _make_synthetic_ohlcv(n=60, seed=1):
    rng = np.random.default_rng(seed)
    close = 100 + rng.normal(0, 1, size=n).cumsum()
    high = close + rng.uniform(0.1, 1.0, size=n)
    low = close - rng.uniform(0.1, 1.0, size=n)
    open_ = close + rng.uniform(-0.5, 0.5, size=n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


def test_add_indicators_includes_volume_ratio():
    """add_indicators がボリューム前期比を計算"""
    df = _make_synthetic_ohlcv(n=60, seed=42)
    df["volume"] = np.random.default_rng(42).uniform(100, 1000, size=60)

    result = add_indicators(df)

    assert "volume_ratio" in result.columns
    # volume_ratio は volume / volume.shift(1)
    # 1行目は NaN（前期なし）
    assert pd.isna(result.iloc[0]["volume_ratio"])
    # 2行目以降は数値
    assert result.iloc[1]["volume_ratio"] > 0


def test_add_indicators_adds_expected_columns_with_valid_ranges():
    df = _make_synthetic_ohlcv()
    result = add_indicators(df)

    expected_columns = {
        "adx", "rsi", "bb_upper", "bb_mid", "bb_lower",
        "atr", "donchian_upper", "donchian_lower", "sma20",
    }
    assert expected_columns.issubset(result.columns)

    tail = result.dropna(subset=["rsi", "bb_upper", "bb_mid", "bb_lower", "atr"])
    assert len(tail) > 0
    assert (tail["rsi"] >= 0).all() and (tail["rsi"] <= 100).all()
    assert (tail["bb_upper"] >= tail["bb_mid"]).all()
    assert (tail["bb_mid"] >= tail["bb_lower"]).all()
    assert (tail["atr"] >= 0).all()
