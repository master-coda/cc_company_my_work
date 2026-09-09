# Crypto Trading Logic Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pandas-based backtesting system that compares a trend-following (breakout) strategy against a mean-reversion strategy on 1h BTC/USDT candles, so we can decide which one (if either) is worth taking into paper trading.

**Architecture:** A new `crypto-paper-trading-bot/` project with independent, unit-tested modules — data fetching (ccxt + CSV cache), indicator calculation (thin wrapper over the `ta` library), two strategy modules sharing a common `Position` interface, a bar-by-bar backtest engine, a metrics evaluator, a parameter grid search, and a thin orchestration script that ties them together into a train/test comparison report.

**Tech Stack:** Python 3.x, ccxt, pandas, ta, pytest.

**Spec:** `docs/superpowers/specs/2026-09-10-crypto-trading-logic-design.md`

## Global Constraints

- Timeframe: 1h candles (primary); this plan does not implement the 4h comparison — it's a follow-up run of the same code with `timeframe="4h"`.
- Data: Binance BTC/USDT via ccxt, ~2 years of history.
- Train/test split: first ~75% of the 2-year window is the training period, last ~25% is the test period (matches the spec's "1.5y train / 0.5y test" on a 2y window).
- Initial capital: 50,000 (JPY-equivalent virtual capital from the spec, used as a plain number here since the backtest runs on USDT-quoted data).
- Risk per trade: 0.5% of current equity (`risk_per_trade=0.005`).
- Fees: 0.1% per fill (`fee_rate=0.001`), applied on both entry and exit.
- Slippage: 0.05% per fill (`slippage_rate=0.0005`) — the spec required *some* slippage assumption but didn't pin a number; this is the plan's concrete choice.
- No lookahead: entry signals are computed from bar `i`'s close, but the position is opened at bar `i+1`'s open.
- Backtest engine is a custom pandas-based implementation — no `vectorbt` or similar.
- Missing-candle handling is flag-only, not drop-then-reindex: the spec says gaps should be flagged and excluded, but dropping rows would break the integer-index alignment `backtest_engine.py` relies on (`entry_index`, `i+1` lookahead). This plan detects and warns on gaps (`detect_gaps`) without removing rows — a disclosed simplification, acceptable because BTC/USDT trades continuously and real gaps should be rare.
- Of the spec's two listed exit-rule alternatives for mean-reversion ("SMA20 reversion, or fixed 1:1.5 RR — either one"), this plan implements the fixed-RR variant for determinism and to keep both strategies' risk models ATR-based and structurally symmetric.

---

## Task 1: Project Scaffolding + Data Fetcher

**Files:**
- Create: `crypto-paper-trading-bot/requirements.txt`
- Create: `crypto-paper-trading-bot/conftest.py`
- Create: `crypto-paper-trading-bot/src/__init__.py`
- Create: `crypto-paper-trading-bot/src/data_fetcher.py`
- Test: `crypto-paper-trading-bot/tests/test_data_fetcher.py`
- Modify: `.gitignore` (repo root)

**Interfaces:**
- Produces: `fetch_ohlcv(exchange, symbol: str, timeframe: str, since_ms: int, until_ms: int, limit: int = 1000, max_retries: int = 5, sleep_fn=time.sleep) -> pd.DataFrame` with columns `["timestamp", "open", "high", "low", "close", "volume"]`, sorted ascending, deduplicated, filtered to `timestamp < until_ms`. Retries each page fetch up to `max_retries` times with exponential backoff (via `sleep_fn`, injectable for tests) before giving up.
- Produces: `fetch_ohlcv_cached(exchange, symbol: str, timeframe: str, since_ms: int, until_ms: int, cache_path: str) -> pd.DataFrame` — same shape, reads from `cache_path` if it exists, otherwise fetches and writes it. Prints a warning if `detect_gaps` finds any.
- Produces: `detect_gaps(df: pd.DataFrame, timeframe: str) -> pd.DataFrame` — rows whose gap from the previous row exceeds the expected candle interval for `timeframe`.
- `exchange` is any object exposing `.fetch_ohlcv(symbol, timeframe, since, limit) -> list[list]` (duck-typed so tests don't need a real ccxt exchange).

- [ ] **Step 1: Create the project directory structure**

```bash
mkdir -p "crypto-paper-trading-bot/src/strategies"
mkdir -p "crypto-paper-trading-bot/tests"
mkdir -p "crypto-paper-trading-bot/data"
mkdir -p "crypto-paper-trading-bot/reports"
touch "crypto-paper-trading-bot/src/__init__.py"
touch "crypto-paper-trading-bot/src/strategies/__init__.py"
```

- [ ] **Step 2: Create `requirements.txt`**

```
ccxt
pandas
ta
pytest
```

- [ ] **Step 2b: Install dependencies**

Run (from `crypto-paper-trading-bot/`): `pip install -r requirements.txt`
Expected: `ccxt`, `pandas`, `ta`, and `pytest` install successfully. All later `pytest` runs in this plan assume these are installed.

- [ ] **Step 3: Create `conftest.py` at the project root**

```python
# Empty on purpose: its presence makes pytest add this directory's
# parent to sys.path, so `from src...` and `from run_backtest import ...`
# both resolve when running `pytest` from crypto-paper-trading-bot/.
```

- [ ] **Step 4: Add the data cache directory to `.gitignore`**

Append to `.gitignore` at the repo root:

```
crypto-paper-trading-bot/data/*.csv
crypto-paper-trading-bot/reports/*.json
```

- [ ] **Step 5: Write the failing tests for `data_fetcher.py`**

Create `crypto-paper-trading-bot/tests/test_data_fetcher.py`:

```python
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
```

- [ ] **Step 6: Run tests to verify they fail**

Run (from `crypto-paper-trading-bot/`): `pytest tests/test_data_fetcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data_fetcher'`

- [ ] **Step 7: Implement `src/data_fetcher.py`**

```python
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
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_data_fetcher.py -v`
Expected: PASS (4 tests)

- [ ] **Step 9: Commit**

```bash
git add crypto-paper-trading-bot/ .gitignore
git commit -m "feat: add crypto-paper-trading-bot scaffolding and data fetcher"
```

---

## Task 2: Indicators

**Files:**
- Create: `crypto-paper-trading-bot/src/indicators.py`
- Test: `crypto-paper-trading-bot/tests/test_indicators.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `add_indicators(df: pd.DataFrame) -> pd.DataFrame` where `df` has columns `open, high, low, close` (and may have `timestamp`/`volume`, ignored). Returns a copy with added columns: `adx, rsi, bb_upper, bb_mid, bb_lower, atr, donchian_upper, donchian_lower, sma20`.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_indicators.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_indicators.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.indicators'`

- [ ] **Step 3: Implement `src/indicators.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_indicators.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add crypto-paper-trading-bot/src/indicators.py crypto-paper-trading-bot/tests/test_indicators.py
git commit -m "feat: add indicator calculation module"
```

---

## Task 3: Position Dataclass + Trend-Following Strategy

**Files:**
- Create: `crypto-paper-trading-bot/src/position.py`
- Create: `crypto-paper-trading-bot/src/strategies/trend_following.py`
- Test: `crypto-paper-trading-bot/tests/test_trend_following.py`

**Interfaces:**
- Consumes: indicator columns produced by Task 2 (`adx`, `atr`, `donchian_upper`, `donchian_lower`).
- Produces: `Position` dataclass with fields `direction: Literal["long","short"], entry_index: int, entry_price: float, stop_price: float, target_price: Optional[float]`.
- Produces: `trend_following.add_entry_signals(df, adx_threshold: float = 20.0) -> pd.DataFrame` (adds column `entry_signal` with values `"long"`, `"short"`, or `None`).
- Produces: `trend_following.open_position(entry_index: int, entry_bar: pd.Series, direction: str, atr_multiplier: float = 2.0, **_) -> Position`.
- Produces: `trend_following.check_exit(position: Position, bar: pd.Series, atr_multiplier: float = 2.0, **_) -> Optional[float]` — mutates `position.stop_price` to trail, returns the exit price when the trailing stop is hit, else `None`.
- These three function names/signatures are what `backtest_engine.py` (Task 5) calls on any strategy module.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_trend_following.py`:

```python
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


def test_check_exit_trails_stop_and_triggers_on_breach():
    position = Position(direction="long", entry_index=0, entry_price=100.0, stop_price=90.0, target_price=None)
    bar_1 = pd.Series({"high": 105.0, "low": 104.0, "atr": 2.0})

    exit_price = trend_following.check_exit(position, bar_1, atr_multiplier=2.0)

    assert exit_price is None
    assert position.stop_price == 101.0  # 105 - 2*2, trailed up from 90

    bar_2 = pd.Series({"high": 101.5, "low": 100.5, "atr": 2.0})
    exit_price = trend_following.check_exit(position, bar_2, atr_multiplier=2.0)

    assert exit_price == 101.0  # low (100.5) breached the trailed stop (101.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trend_following.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.position'`

- [ ] **Step 3: Implement `src/position.py`**

```python
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Position:
    direction: Literal["long", "short"]
    entry_index: int
    entry_price: float
    stop_price: float
    target_price: Optional[float] = None
```

- [ ] **Step 4: Implement `src/strategies/trend_following.py`**

```python
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
    if direction == "long":
        stop_price = entry_price - atr_multiplier * entry_bar["atr"]
    else:
        stop_price = entry_price + atr_multiplier * entry_bar["atr"]
    return Position(direction=direction, entry_index=entry_index, entry_price=entry_price, stop_price=stop_price, target_price=None)


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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_trend_following.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add crypto-paper-trading-bot/src/position.py crypto-paper-trading-bot/src/strategies/trend_following.py crypto-paper-trading-bot/tests/test_trend_following.py
git commit -m "feat: add Position dataclass and trend-following strategy"
```

---

## Task 4: Mean-Reversion Strategy

**Files:**
- Create: `crypto-paper-trading-bot/src/strategies/mean_reversion.py`
- Test: `crypto-paper-trading-bot/tests/test_mean_reversion.py`

**Interfaces:**
- Consumes: `Position` from Task 3 (`src/position.py`); indicator columns `adx`, `rsi`, `bb_upper`, `bb_lower`, `atr`.
- Produces: `mean_reversion.add_entry_signals(df, adx_threshold: float = 20.0, rsi_oversold: float = 30.0, rsi_overbought: float = 70.0, **_) -> pd.DataFrame` (adds `entry_signal`).
- Produces: `mean_reversion.open_position(entry_index: int, entry_bar: pd.Series, direction: str, stop_atr_multiplier: float = 1.5, rr_ratio: float = 1.5, **_) -> Position` — sets a fixed `stop_price` and `target_price` at entry (no trailing).
- Produces: `mean_reversion.check_exit(position: Position, bar: pd.Series, **_) -> Optional[float]`.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_mean_reversion.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mean_reversion.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.strategies.mean_reversion'`

- [ ] **Step 3: Implement `src/strategies/mean_reversion.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mean_reversion.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add crypto-paper-trading-bot/src/strategies/mean_reversion.py crypto-paper-trading-bot/tests/test_mean_reversion.py
git commit -m "feat: add mean-reversion strategy"
```

---

## Task 5: Backtest Engine

**Files:**
- Create: `crypto-paper-trading-bot/src/backtest_engine.py`
- Test: `crypto-paper-trading-bot/tests/test_backtest_engine.py`

**Interfaces:**
- Consumes: `Position` (Task 3); any strategy module exposing `add_entry_signals(df, **params)`, `open_position(entry_index, entry_bar, direction, **params)`, `check_exit(position, bar, **params)` (Tasks 3-4).
- Produces: `run_backtest(df: pd.DataFrame, strategy, strategy_params: dict, initial_capital: float = 50000.0, risk_per_trade: float = 0.005, fee_rate: float = 0.001, slippage_rate: float = 0.0005) -> pd.DataFrame` — a trade log with columns `direction, entry_index, exit_index, entry_price, exit_price, position_size, pnl`. This is what `evaluator.py` (Task 6) and `parameter_search.py` (Task 7) consume.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_backtest_engine.py`:

```python
import pandas as pd
from src.backtest_engine import run_backtest
from src.position import Position


class FakeStrategy:
    def add_entry_signals(self, df, **params):
        df = df.copy()
        df["entry_signal"] = [None, "long", None, None, None]
        return df

    def open_position(self, entry_index, entry_bar, direction, **params):
        return Position(
            direction=direction,
            entry_index=entry_index,
            entry_price=entry_bar["open"],
            stop_price=entry_bar["open"] - 10.0,
            target_price=None,
        )

    def check_exit(self, position, bar, **params):
        if bar.name == 3:
            return bar["close"]
        return None


def _make_df():
    return pd.DataFrame({
        "open":  [100.0, 101.0, 102.0, 103.0, 104.0],
        "high":  [100.5, 101.5, 102.5, 103.5, 104.5],
        "low":   [99.5, 100.5, 101.5, 102.5, 103.5],
        "close": [100.2, 101.2, 102.2, 103.2, 104.2],
    })


def test_run_backtest_opens_and_closes_single_trade_no_fees():
    trades = run_backtest(
        _make_df(),
        FakeStrategy(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.0,
        slippage_rate=0.0,
    )

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "long"
    assert trade["entry_index"] == 2
    assert trade["exit_index"] == 3
    assert trade["entry_price"] == 102.0
    assert trade["exit_price"] == 103.2
    # risk_amount = 50000 * 0.005 = 250; stop_distance = 10 -> position_size = 25
    assert trade["position_size"] == 25.0
    # pnl = 25 * (103.2 - 102.0) = 30.0
    assert abs(trade["pnl"] - 30.0) < 1e-9


def test_run_backtest_applies_fees_and_slippage():
    trades = run_backtest(
        _make_df(),
        FakeStrategy(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    trade = trades.iloc[0]
    # entry_price = 102 * 1.0005 = 102.051; exit_price = 103.2 * 0.9995 = 103.1484
    assert abs(trade["entry_price"] - 102.051) < 1e-9
    assert abs(trade["exit_price"] - 103.1484) < 1e-9
    gross_pnl = 25.0 * (103.1484 - 102.051)
    fees = (102.051 + 103.1484) * 25.0 * 0.001
    assert abs(trade["pnl"] - (gross_pnl - fees)) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backtest_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.backtest_engine'`

- [ ] **Step 3: Implement `src/backtest_engine.py`**

```python
import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    strategy,
    strategy_params: dict,
    initial_capital: float = 50000.0,
    risk_per_trade: float = 0.005,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> pd.DataFrame:
    df = strategy.add_entry_signals(df, **strategy_params)
    trades = []
    equity = initial_capital
    position = None

    for i in range(len(df) - 1):
        bar = df.iloc[i]
        next_bar = df.iloc[i + 1]

        if position is not None:
            exit_price = strategy.check_exit(position, bar, **strategy_params)
            if exit_price is not None:
                trade = _close_trade(position, exit_price, equity, risk_per_trade, fee_rate, slippage_rate, i)
                trades.append(trade)
                equity += trade["pnl"]
                position = None
                continue

        if position is None and bar["entry_signal"] in ("long", "short"):
            position = strategy.open_position(i + 1, next_bar, bar["entry_signal"], **strategy_params)

    return pd.DataFrame(trades)


def _close_trade(position, exit_price, equity, risk_per_trade, fee_rate, slippage_rate, exit_index):
    direction_sign = 1 if position.direction == "long" else -1
    entry_price = position.entry_price * (1 + direction_sign * slippage_rate)
    exit_price = exit_price * (1 - direction_sign * slippage_rate)

    stop_distance = abs(position.entry_price - position.stop_price)
    risk_amount = equity * risk_per_trade
    position_size = risk_amount / stop_distance if stop_distance > 0 else 0.0

    gross_pnl = direction_sign * (exit_price - entry_price) * position_size
    fees = (entry_price + exit_price) * position_size * fee_rate
    pnl = gross_pnl - fees

    return {
        "direction": position.direction,
        "entry_index": position.entry_index,
        "exit_index": exit_index,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "position_size": position_size,
        "pnl": pnl,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backtest_engine.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add crypto-paper-trading-bot/src/backtest_engine.py crypto-paper-trading-bot/tests/test_backtest_engine.py
git commit -m "feat: add backtest engine"
```

---

## Task 6: Evaluator

**Files:**
- Create: `crypto-paper-trading-bot/src/evaluator.py`
- Test: `crypto-paper-trading-bot/tests/test_evaluator.py`

**Interfaces:**
- Consumes: the trade-log `pd.DataFrame` produced by `run_backtest` (Task 5) — specifically its `pnl` column.
- Produces: `evaluate(trades: pd.DataFrame) -> dict` with keys `total_trades, win_rate, avg_win, avg_loss, risk_reward_ratio, profit_factor, max_drawdown, expectancy`. This exact key set is what `run_backtest.py` (Task 8) puts into the comparison report.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_evaluator.py`:

```python
import pandas as pd
import pytest
from src.evaluator import evaluate


def test_evaluate_computes_expected_metrics():
    trades = pd.DataFrame({"pnl": [100.0, -50.0, 200.0, -50.0, -100.0]})

    metrics = evaluate(trades)

    assert metrics["total_trades"] == 5
    assert metrics["win_rate"] == pytest.approx(0.4)
    assert metrics["avg_win"] == pytest.approx(150.0)
    assert metrics["avg_loss"] == pytest.approx(-200.0 / 3)
    assert metrics["risk_reward_ratio"] == pytest.approx(2.25)
    assert metrics["profit_factor"] == pytest.approx(1.5)
    assert metrics["max_drawdown"] == pytest.approx(150.0)
    assert metrics["expectancy"] == pytest.approx(20.0)


def test_evaluate_handles_empty_trades():
    trades = pd.DataFrame({"pnl": []})

    metrics = evaluate(trades)

    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["risk_reward_ratio"] == 0.0
    assert metrics["profit_factor"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.evaluator'`

- [ ] **Step 3: Implement `src/evaluator.py`**

```python
import pandas as pd


def evaluate(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "risk_reward_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0,
        }

    wins = trades[trades["pnl"] > 0]["pnl"]
    losses = trades[trades["pnl"] < 0]["pnl"]

    total_trades = len(trades)
    win_rate = len(wins) / total_trades
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0
    risk_reward_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else 0.0

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else 0.0

    equity_curve = trades["pnl"].cumsum()
    running_max = equity_curve.cummax()
    drawdown = equity_curve - running_max
    max_drawdown = abs(drawdown.min())

    expectancy = trades["pnl"].mean()

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "expectancy": expectancy,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add crypto-paper-trading-bot/src/evaluator.py crypto-paper-trading-bot/tests/test_evaluator.py
git commit -m "feat: add backtest metrics evaluator"
```

---

## Task 7: Parameter Grid Search

**Files:**
- Create: `crypto-paper-trading-bot/src/parameter_search.py`
- Test: `crypto-paper-trading-bot/tests/test_parameter_search.py`

**Interfaces:**
- Consumes: `run_backtest` (Task 5), `evaluate` (Task 6).
- Produces: `grid_search(df_train: pd.DataFrame, strategy, param_grid: dict, metric_key: str = "expectancy") -> dict` — returns the `param_grid` combination (as a `dict`) that maximizes `evaluate(...)[metric_key]` on `df_train`. This is what `run_backtest.py` (Task 8) calls per strategy before evaluating on the test split.

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_parameter_search.py`:

```python
import pandas as pd
from src.parameter_search import grid_search
from src.position import Position


class FakeStrategyForGridSearch:
    def add_entry_signals(self, df, **params):
        df = df.copy()
        df["entry_signal"] = [None, "long", None, None]
        return df

    def open_position(self, entry_index, entry_bar, direction, **params):
        return Position(
            direction=direction,
            entry_index=entry_index,
            entry_price=entry_bar["open"],
            stop_price=entry_bar["open"] - 10.0,
            target_price=None,
        )

    def check_exit(self, position, bar, threshold=1, **params):
        # Payoff peaks at threshold == 2 by construction, so the search
        # must actually compare all three, not just pick an endpoint.
        payoff = {1: 5.0, 2: 50.0, 3: 20.0}
        if bar.name == 2:
            return position.entry_price + payoff[threshold]
        return None


def test_grid_search_picks_best_scoring_params():
    df = pd.DataFrame({
        "open":  [100.0, 101.0, 102.0, 103.0],
        "high":  [100.5, 101.5, 102.5, 103.5],
        "low":   [99.5, 100.5, 101.5, 102.5],
        "close": [100.2, 101.2, 102.2, 103.2],
    })

    best = grid_search(df, FakeStrategyForGridSearch(), param_grid={"threshold": [1, 2, 3]})

    assert best == {"threshold": 2}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parameter_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.parameter_search'`

- [ ] **Step 3: Implement `src/parameter_search.py`**

```python
import itertools
import pandas as pd
from src.backtest_engine import run_backtest
from src.evaluator import evaluate


def grid_search(df_train: pd.DataFrame, strategy, param_grid: dict, metric_key: str = "expectancy") -> dict:
    keys = list(param_grid.keys())
    best_params = None
    best_score = float("-inf")

    for values in itertools.product(*param_grid.values()):
        params = dict(zip(keys, values))
        trades = run_backtest(df_train.copy(), strategy, strategy_params=params)
        metrics = evaluate(trades)
        score = metrics[metric_key]
        if score > best_score:
            best_score = score
            best_params = params

    return best_params
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parameter_search.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add crypto-paper-trading-bot/src/parameter_search.py crypto-paper-trading-bot/tests/test_parameter_search.py
git commit -m "feat: add parameter grid search"
```

---

## Task 8: Orchestration Script (Train/Test Comparison Report)

**Files:**
- Create: `crypto-paper-trading-bot/run_backtest.py`
- Test: `crypto-paper-trading-bot/tests/test_run_backtest.py`

**Interfaces:**
- Consumes: `add_indicators` (Task 2), `trend_following` / `mean_reversion` (Tasks 3-4), `run_backtest` (Task 5), `evaluate` (Task 6), `grid_search` (Task 7), `fetch_ohlcv_cached` (Task 1).
- Produces: `split_train_test(df: pd.DataFrame, train_fraction: float = 0.75) -> tuple[pd.DataFrame, pd.DataFrame]`.
- Produces: `build_comparison_report(raw_df: pd.DataFrame) -> dict` shaped `{"trend_following": {"best_params": {...}, "train": {...metrics}, "test": {...metrics}}, "mean_reversion": {...}}`. This is the report both `main()` (live run) and the test consume.
- `main()` fetches real Binance data via ccxt and writes `reports/comparison_report.json`; it is not unit tested (network I/O boundary).

- [ ] **Step 1: Write the failing test**

Create `crypto-paper-trading-bot/tests/test_run_backtest.py`:

```python
import numpy as np
import pandas as pd
from run_backtest import build_comparison_report, split_train_test


def test_split_train_test_uses_first_75_percent_as_train():
    df = pd.DataFrame({"close": range(100)})

    train_df, test_df = split_train_test(df, train_fraction=0.75)

    assert len(train_df) == 75
    assert len(test_df) == 25
    assert train_df["close"].iloc[-1] == 74
    assert test_df["close"].iloc[0] == 75


def test_build_comparison_report_structure():
    rng = np.random.default_rng(42)
    n = 200
    close = 100 + rng.normal(0, 1, size=n).cumsum()
    high = close + rng.uniform(0.1, 1.0, size=n)
    low = close - rng.uniform(0.1, 1.0, size=n)
    open_ = close + rng.uniform(-0.5, 0.5, size=n)
    raw_df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    report = build_comparison_report(raw_df)

    assert set(report.keys()) == {"trend_following", "mean_reversion"}
    expected_metric_keys = {
        "total_trades", "win_rate", "avg_win", "avg_loss",
        "risk_reward_ratio", "profit_factor", "max_drawdown", "expectancy",
    }
    for name in report:
        assert set(report[name].keys()) == {"best_params", "train", "test"}
        assert set(report[name]["train"].keys()) == expected_metric_keys
        assert set(report[name]["test"].keys()) == expected_metric_keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_run_backtest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'run_backtest'`

- [ ] **Step 3: Implement `run_backtest.py`**

```python
import json
import os
import time

import ccxt
import pandas as pd

from src import data_fetcher, indicators
from src.strategies import trend_following, mean_reversion
from src.backtest_engine import run_backtest
from src.evaluator import evaluate
from src.parameter_search import grid_search

TREND_FOLLOWING_GRID = {
    "adx_threshold": [15, 20, 25],
    "atr_multiplier": [1.5, 2.0, 2.5],
}

MEAN_REVERSION_GRID = {
    "adx_threshold": [15, 20, 25],
    "rsi_oversold": [25, 30, 35],
    "rsi_overbought": [65, 70, 75],
    "stop_atr_multiplier": [1.0, 1.5, 2.0],
    "rr_ratio": [1.0, 1.5, 2.0],
}

STRATEGIES = {
    "trend_following": (trend_following, TREND_FOLLOWING_GRID),
    "mean_reversion": (mean_reversion, MEAN_REVERSION_GRID),
}


def split_train_test(df: pd.DataFrame, train_fraction: float = 0.75) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_index = int(len(df) * train_fraction)
    train_df = df.iloc[:split_index].reset_index(drop=True)
    test_df = df.iloc[split_index:].reset_index(drop=True)
    return train_df, test_df


def build_comparison_report(raw_df: pd.DataFrame) -> dict:
    df = indicators.add_indicators(raw_df)
    train_df, test_df = split_train_test(df)

    report = {}
    for name, (strategy, param_grid) in STRATEGIES.items():
        best_params = grid_search(train_df, strategy, param_grid)
        train_trades = run_backtest(train_df.copy(), strategy, strategy_params=best_params)
        test_trades = run_backtest(test_df.copy(), strategy, strategy_params=best_params)
        report[name] = {
            "best_params": best_params,
            "train": evaluate(train_trades),
            "test": evaluate(test_trades),
        }

    return report


def main():
    exchange = ccxt.binance()
    until_ms = int(time.time() * 1000)
    since_ms = until_ms - 2 * 365 * 24 * 60 * 60 * 1000  # 2 years back

    raw_df = data_fetcher.fetch_ohlcv_cached(
        exchange, "BTC/USDT", "1h", since_ms, until_ms, "data/btc_usdt_1h.csv"
    )

    report = build_comparison_report(raw_df)

    os.makedirs("reports", exist_ok=True)
    with open("reports/comparison_report.json", "w") as f:
        json.dump(report, f, indent=2, default=float)

    for name, result in report.items():
        print(f"=== {name} ===")
        print("best_params:", result["best_params"])
        print("train:", result["train"])
        print("test:", result["test"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_run_backtest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS (all tests across all tasks)

- [ ] **Step 6: Commit**

```bash
git add crypto-paper-trading-bot/run_backtest.py crypto-paper-trading-bot/tests/test_run_backtest.py
git commit -m "feat: add train/test comparison orchestration script"
```

- [ ] **Step 7: Run the live comparison against real Binance data**

Run (from `crypto-paper-trading-bot/`): `pip install -r requirements.txt && python run_backtest.py`
Expected: prints `best_params`/`train`/`test` metrics for both strategies and writes `reports/comparison_report.json`. This run is exploratory — its output is the input to the next decision (which strategy, if either, moves to paper trading), not something this plan evaluates automatically.
