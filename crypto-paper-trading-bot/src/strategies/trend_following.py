from typing import Optional
import pandas as pd
from src.position import Position


def add_entry_signals(df: pd.DataFrame, adx_threshold: float = 20.0, **_) -> pd.DataFrame:
    df = df.copy()
    is_trending = df["adx"] > adx_threshold
    # shift(1): breakout is measured against the *previous* bar's channel,
    # otherwise the current bar's own high/low would trivially satisfy it.
    breaks_high = df["close"] > df["donchian_upper"].shift(1)
    breaks_low = df["close"] < df["donchian_lower"].shift(1)

    signal = pd.Series([None] * len(df), index=df.index, dtype=object)
    signal[is_trending & breaks_high] = "long"
    signal[is_trending & breaks_low] = "short"
    df["entry_signal"] = signal
    return df


def open_position(entry_index: int, entry_bar: pd.Series, direction: str, atr_multiplier: float = 2.0, **_) -> Position:
    entry_price = entry_bar["open"]
    atr_distance = atr_multiplier * entry_bar["atr"]

    if direction == "long":
        stop_price = entry_price - atr_distance
        target_price = entry_price + atr_distance
    else:
        stop_price = entry_price + atr_distance
        target_price = entry_price - atr_distance

    return Position(direction=direction, entry_index=entry_index, entry_price=entry_price, stop_price=stop_price, target_price=target_price)


def check_exit(position: Position, bar: pd.Series, atr_multiplier: float = 2.0, **_) -> Optional[float]:
    if position.direction == "long":
        trailing_stop = bar["high"] - atr_multiplier * bar["atr"]
        position.stop_price = max(position.stop_price, trailing_stop)
        if bar["low"] <= position.stop_price:
            return position.stop_price
    else:
        trailing_stop = bar["low"] + atr_multiplier * bar["atr"]
        position.stop_price = min(position.stop_price, trailing_stop)
        if bar["high"] >= position.stop_price:
            return position.stop_price
    return None
