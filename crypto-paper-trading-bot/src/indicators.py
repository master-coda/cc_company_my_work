import pandas as pd
from ta.trend import ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange, DonchianChannel


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["adx"] = adx.adx()

    rsi = RSIIndicator(close=df["close"], window=14)
    df["rsi"] = rsi.rsi()

    bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()

    atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["atr"] = atr.average_true_range()

    donchian = DonchianChannel(high=df["high"], low=df["low"], close=df["close"], window=20)
    df["donchian_upper"] = donchian.donchian_channel_hband()
    df["donchian_lower"] = donchian.donchian_channel_lband()

    df["sma20"] = df["close"].rolling(window=20).mean()

    return df
