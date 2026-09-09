import pandas as pd
from src.position import Position
from src.strategies import mean_reversion


def test_add_entry_signals_fires_on_lower_band_touch_and_oversold_rsi():
    df = pd.DataFrame({
        "close":    [100, 90],
        "adx":      [10,  10],   # ranging
        "bb_upper": [110, 110],
        "bb_lower": [95,  95],
        "rsi":      [50,  25],   # oversold on row 2
    })

    result = mean_reversion.add_entry_signals(df, adx_threshold=20.0, rsi_oversold=30.0, rsi_overbought=70.0)

    assert result["entry_signal"].tolist() == [None, "long"]


def test_add_entry_signals_requires_ranging_market():
    df = pd.DataFrame({
        "close":    [90],
        "adx":      [30],   # trending, not ranging
        "bb_upper": [110],
        "bb_lower": [95],
        "rsi":      [25],
    })

    result = mean_reversion.add_entry_signals(df, adx_threshold=20.0)

    assert result["entry_signal"].tolist() == [None]


def test_open_position_sets_fixed_stop_and_target():
    entry_bar = pd.Series({"open": 100.0, "atr": 4.0})

    position = mean_reversion.open_position(entry_index=5, entry_bar=entry_bar, direction="long", stop_atr_multiplier=1.5, rr_ratio=1.5)

    assert position.entry_price == 100.0
    assert position.stop_price == 94.0     # 100 - 1.5*4
    assert position.target_price == 109.0  # 100 + (1.5*4)*1.5


def test_check_exit_triggers_on_stop_or_target():
    position = Position(direction="long", entry_index=0, entry_price=100.0, stop_price=94.0, target_price=109.0)

    no_exit_bar = pd.Series({"high": 105.0, "low": 96.0})
    assert mean_reversion.check_exit(position, no_exit_bar) is None

    target_bar = pd.Series({"high": 110.0, "low": 105.0})
    assert mean_reversion.check_exit(position, target_bar) == 109.0
