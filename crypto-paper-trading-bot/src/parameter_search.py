import itertools
import pandas as pd
from src.backtest_engine import run_backtest
from src.evaluator import evaluate


def grid_search(
    df_train: pd.DataFrame,
    strategy,
    param_grid: dict,
    metric_key: str = "expectancy",
    min_trades: int = 30,
) -> dict:
    keys = list(param_grid.keys())
    best_params = None
    best_score = float("-inf")
    fallback_best_params = None
    fallback_best_score = float("-inf")

    for values in itertools.product(*param_grid.values()):
        params = dict(zip(keys, values))
        trades = run_backtest(df_train.copy(), strategy, strategy_params=params)
        metrics = evaluate(trades)
        score = metrics[metric_key]

        if score > fallback_best_score:
            fallback_best_score = score
            fallback_best_params = params

        if metrics["total_trades"] >= min_trades and score > best_score:
            best_score = score
            best_params = params

    return best_params if best_params is not None else fallback_best_params
