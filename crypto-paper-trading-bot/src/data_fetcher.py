import os
import time
import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def _fetch_page_with_retry(exchange, symbol, timeframe, since, limit, max_retries, sleep_fn):
    last_error = None
    for attempt in range(max_retries):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        except Exception as error:
            last_error = error
            if attempt < max_retries - 1:
                sleep_fn(2 ** attempt)
    raise last_error


def fetch_ohlcv(
    exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int,
    limit: int = 1000,
    max_retries: int = 5,
    sleep_fn=time.sleep,
) -> pd.DataFrame:
    all_candles = []
    cursor = since_ms

    while cursor < until_ms:
        batch = _fetch_page_with_retry(exchange, symbol, timeframe, cursor, limit, max_retries, sleep_fn)
        if not batch:
            break
        all_candles.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        if len(batch) < limit:
            break

    df = pd.DataFrame(all_candles, columns=OHLCV_COLUMNS)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    df = df[df["timestamp"] < until_ms].reset_index(drop=True)
    return df


def detect_gaps(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    interval_ms = TIMEFRAME_MS[timeframe]
    is_gap = df["timestamp"].diff() > interval_ms
    return df[is_gap]


def fetch_ohlcv_cached(exchange, symbol: str, timeframe: str, since_ms: int, until_ms: int, cache_path: str) -> pd.DataFrame:
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path)
    else:
        df = fetch_ohlcv(exchange, symbol, timeframe, since_ms, until_ms)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df.to_csv(cache_path, index=False)

    gaps = detect_gaps(df, timeframe)
    if len(gaps) > 0:
        print(f"warning: {len(gaps)} gap(s) detected in {symbol} {timeframe} data")

    return df
