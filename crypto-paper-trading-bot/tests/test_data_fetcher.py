import os
import pandas as pd
from src.data_fetcher import fetch_ohlcv, fetch_ohlcv_cached, detect_gaps


class FakeExchange:
    def __init__(self, batches):
        self._batches = batches
        self.calls = 0

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls += 1
        if self.calls > len(self._batches):
            return []
        return self._batches[self.calls - 1]


def test_fetch_ohlcv_paginates_and_dedupes():
    batch1 = [[1000 + i * 60000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(3)]
    batch2 = [[1000 + (i + 3) * 60000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(2)]
    exchange = FakeExchange([batch1, batch2])

    df = fetch_ohlcv(exchange, "BTC/USDT", "1h", since_ms=1000, until_ms=1000 + 5 * 60000, limit=3)

    assert list(df["timestamp"]) == [1000, 61000, 121000, 181000, 241000]
    assert exchange.calls == 2


def test_fetch_ohlcv_retries_on_transient_error_then_succeeds():
    batch = [[1000 + i * 60000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(2)]

    class FlakyExchange:
        def __init__(self):
            self.calls = 0

        def fetch_ohlcv(self, symbol, timeframe, since, limit):
            self.calls += 1
            if self.calls < 3:
                raise ConnectionError("transient network error")
            return batch

    exchange = FlakyExchange()

    df = fetch_ohlcv(
        exchange, "BTC/USDT", "1h", since_ms=1000, until_ms=1000 + 2 * 60000,
        sleep_fn=lambda seconds: None,
    )

    assert exchange.calls == 3
    assert list(df["timestamp"]) == [1000, 61000]


def test_fetch_ohlcv_cached_reads_from_disk_on_second_call(tmp_path):
    batch = [[1000 + i * 60000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(5)]
    exchange = FakeExchange([batch])
    cache_path = str(tmp_path / "btc_usdt_1h.csv")

    df1 = fetch_ohlcv_cached(exchange, "BTC/USDT", "1h", 1000, 1000 + 5 * 60000, cache_path)
    assert exchange.calls == 1
    assert os.path.exists(cache_path)

    df2 = fetch_ohlcv_cached(exchange, "BTC/USDT", "1h", 1000, 1000 + 5 * 60000, cache_path)
    assert exchange.calls == 1
    pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))


def test_detect_gaps_flags_rows_with_missing_candles():
    df = pd.DataFrame({"timestamp": [0, 60000, 120000, 300000]})  # gap before the last row

    gaps = detect_gaps(df, "1m")

    assert list(gaps["timestamp"]) == [300000]
