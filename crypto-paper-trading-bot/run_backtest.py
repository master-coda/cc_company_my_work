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
    "rr_ratio": [1.5, 2.0, 2.5],
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
