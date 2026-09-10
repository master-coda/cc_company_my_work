import pandas as pd
from src.position import Position
from src.strategies import trend_following


def test_add_entry_signals_fires_on_adx_and_donchian_breakout():
    df = pd.DataFrame({
        "close":           [100, 101, 102, 110],
        "adx":             [25,  25,  25,  25],
        "donchian_upper":  [105, 105, 105, 105],
        "donchian_lower":  [95,  95,  95,  95],
    })

    result = trend_following.add_entry_signals(df, adx_threshold=20.0)

    assert result["entry_signal"].tolist() == [None, None, None, "long"]


def test_add_entry_signals_requires_trend_strength():
    df = pd.DataFrame({
        "close":           [100, 110],
        "adx":             [10,  10],   # below threshold: ranging, not trending
        "donchian_upper":  [105, 105],
        "donchian_lower":  [95,  95],
    })

    result = trend_following.add_entry_signals(df, adx_threshold=20.0)

    assert result["entry_signal"].tolist() == [None, None]


def test_open_position_sets_target_price_for_long():
    entry_bar = pd.Series({"open": 100.0, "atr": 5.0})

    position = trend_following.open_position(
        entry_index=10,
        entry_bar=entry_bar,
        direction="long",
        atr_multiplier=2.0
    )

    assert position.entry_price == 100.0
    assert position.stop_price == 90.0
    assert position.target_price == 110.0


def test_open_position_sets_target_price_for_short():
    entry_bar = pd.Series({"open": 100.0, "atr": 5.0})

    position = trend_following.open_position(
        entry_index=10,
        entry_bar=entry_bar,
        direction="short",
        atr_multiplier=2.0
    )

    assert position.entry_price == 100.0
    assert position.stop_price == 110.0
    assert position.target_price == 90.0


def test_check_exit_trails_stop_and_triggers_on_breach():
    position = Position(direction="long", entry_index=0, entry_price=100.0, stop_price=90.0, target_price=None)
    bar_1 = pd.Series({"high": 105.0, "low": 104.0, "atr": 2.0})

    exit_price = trend_following.check_exit(position, bar_1, atr_multiplier=2.0)

    assert exit_price is None
    assert position.stop_price == 101.0  # 105 - 2*2, trailed up from 90

    bar_2 = pd.Series({"high": 101.5, "low": 100.5, "atr": 2.0})
    exit_price = trend_following.check_exit(position, bar_2, atr_multiplier=2.0)

    assert exit_price == 101.0  # low (100.5) breached the trailed stop (101.0)
