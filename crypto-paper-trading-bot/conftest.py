# Empty on purpose: its presence makes pytest add this directory's
# parent to sys.path, so `from src...` and `from run_backtest import ...`
# both resolve when running `pytest` from crypto-paper-trading-bot/.
