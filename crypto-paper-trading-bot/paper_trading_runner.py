#!/usr/bin/env python3
"""
Daily Paper Trading Runner

毎日のペーパートレーディング実行スクリプト
CronCreate で毎日 23:00 UTC に実行
"""

import os
from datetime import datetime
from src.data_fetcher import fetch_ohlcv
from src.indicators import add_indicators
from src.strategies import trend_following
from src.paper_trading import PaperTradingPortfolio
from src.paper_trading_dashboard import generate_dashboard


def run_daily_paper_trading():
    """毎日のペーパートレーディング実行"""
    portfolio_file = "data/paper_trading_portfolio.json"

    # ポートフォリオを復元または初期化
    if os.path.exists(portfolio_file):
        portfolio = PaperTradingPortfolio.load_from_json(portfolio_file)
        print(f"[{datetime.utcnow().isoformat()}Z] Loaded existing portfolio")
    else:
        os.makedirs("data", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        portfolio = PaperTradingPortfolio(initial_capital=30000.0)
        print(f"[{datetime.utcnow().isoformat()}Z] Initialized new portfolio with $30,000")

    try:
        # ポートフォリオをJSON保存
        portfolio.save_to_json(portfolio_file)

        # ダッシュボードを生成
        generate_dashboard(portfolio_file)

        # 統計を出力
        timestamp = datetime.utcnow().isoformat() + "Z"
        print(f"\n=== Paper Trading Status [{timestamp}] ===")
        print(f"Equity: ${portfolio.get_equity():,.2f}")
        print(f"Total PnL: ${portfolio.get_pnl():,.2f}")
        print(f"Total Trades: {portfolio.get_total_trades()}")
        print(f"Win Rate: {portfolio.get_win_rate():.1%}")
        print(f"Dashboard: reports/paper_trading_dashboard.html")
        print(f"========================================\n")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_daily_paper_trading()
