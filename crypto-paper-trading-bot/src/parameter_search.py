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
