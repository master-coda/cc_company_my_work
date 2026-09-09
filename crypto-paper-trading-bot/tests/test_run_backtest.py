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
