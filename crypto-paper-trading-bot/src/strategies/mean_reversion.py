from typing import Optional
import pandas as pd
from src.position import Position


def add_entry_signals(
    df: pd.DataFrame,
    adx_threshold: float = 20.0,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    **_,
) -> pd.DataFrame:
    df = df.copy()
    is_ranging = df["adx"] < adx_threshold
    touches_lower = df["close"] <= df["bb_lower"]
    touches_upper = df["close"] >= df["bb_upper"]

    signal = pd.Series([None] * len(df), index=df.index, dtype=object)
    signal[is_ranging & touches_lower & (df["rsi"] < rsi_oversold)] = "long"
    signal[is_ranging & touches_upper & (df["rsi"] > rsi_overbought)] = "short"
    df["entry_signal"] = signal
    return df


def open_position(
    entry_index: int,
    entry_bar: pd.Series,
    direction: str,
    stop_atr_multiplier: float = 1.5,
    rr_ratio: float = 1.5,
    **_,
) -> Position:
    entry_price = entry_bar["open"]
    stop_distance = stop_atr_multiplier * entry_bar["atr"]
    if direction == "long":
        stop_price = entry_price - stop_distance
        target_price = entry_price + stop_distance * rr_ratio
    else:
        stop_price = entry_price + stop_distance
        target_price = entry_price - stop_distance * rr_ratio
    return Position(direction=direction, entry_index=entry_index, entry_price=entry_price, stop_price=stop_price, target_price=target_price)


def check_exit(position: Position, bar: pd.Series, **_) -> Optional[float]:
    if position.direction == "long":
        if bar["low"] <= position.stop_price:
            return position.stop_price
        if bar["high"] >= position.target_price:
            return position.target_price
    else:
        if bar["high"] >= position.stop_price:
            return position.stop_price
        if bar["low"] <= position.target_price:
            return position.target_price
    return None
