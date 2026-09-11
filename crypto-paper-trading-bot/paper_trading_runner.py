#!/usr/bin/env python3
"""
Daily Paper Trading Runner

毎日のペーパートレーディング実行スクリプト
CronCreate で毎日 23:00 UTC に実行
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
import ccxt
from src.data_fetcher import fetch_ohlcv
from src.indicators import add_indicators
from src.strategies import trend_following
from src.paper_trading import PaperTradingPortfolio
from src.paper_trading_dashboard import generate_dashboard

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def persist_state_to_git(files):
    """状態ファイルをgit commit+pushして永続化。

    リモートルーティン実行は毎回リポジトリを再取得するため、data/配下の
    ポートフォリオがコミットされていないと次回実行時に履歴が消える。
    """
    try:
        subprocess.run(["git", "add"] + files, cwd=SCRIPT_DIR, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m",
             f"chore: update paper trading state ({datetime.utcnow().isoformat()}Z)\n\n"
             "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"],
            cwd=SCRIPT_DIR, capture_output=True, text=True,
        )
        if commit.returncode != 0:
            if "nothing to commit" in commit.stdout:
                return
            print(f"[WARNING] git commit failed: {commit.stdout}{commit.stderr}")
            return
        subprocess.run(["git", "push"], cwd=SCRIPT_DIR, check=True)
        print("[INFO] Persisted paper trading state to git")
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Could not persist state to git: {e}")


def get_chart_data(exchange):
    """BTC/USDT API からチャート用データを取得"""
    import pandas as pd

    try:
        since_ms = int((datetime.utcnow() - timedelta(days=90)).timestamp() * 1000)
        until_ms = int(datetime.utcnow().timestamp() * 1000)

        df = fetch_ohlcv(exchange, "BTC/USDT", "1h", since_ms, until_ms, limit=1000)
        if df.empty:
            return None

        # 日足に集約
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['date'] = df['timestamp'].dt.date
        daily = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()

        # ローソク足データを準備
        candles = []
        for _, row in daily.iterrows():
            candles.append({
                "timestamp": str(row['date']),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume'])
            })

        return candles if candles else None
    except Exception as e:
        print(f"[WARNING] Could not fetch chart data: {e}")
        return None


def run_daily_paper_trading():
    """毎日のペーパートレーディング実行 - リアルなポジション管理"""
    import pandas as pd
    from src.strategies.trend_following import add_entry_signals, open_position, check_exit

    portfolio_file = "data/paper_trading_portfolio.json"
    chart_file = "data/chart_data.json"

    # ポートフォリオを復元または初期化
    if os.path.exists(portfolio_file):
        portfolio = PaperTradingPortfolio.load_from_json(portfolio_file)
        print(f"[{datetime.utcnow().isoformat()}Z] Loaded existing portfolio")
    else:
        os.makedirs("data", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        portfolio = PaperTradingPortfolio(initial_capital=200.0)
        print(f"[{datetime.utcnow().isoformat()}Z] Initialized new portfolio with $200 (¥30,000)")

    exchange = ccxt.binance()
    try:
        # BTC/USDT データを API から取得（最新90日分）
        since_ms = int((datetime.utcnow() - timedelta(days=90)).timestamp() * 1000)
        until_ms = int(datetime.utcnow().timestamp() * 1000)
        df = fetch_ohlcv(exchange, "BTC/USDT", "1h", since_ms, until_ms, limit=1000)
        if df.empty:
            print("[WARNING] No data available")
            return

        df = add_indicators(df)
        df = add_entry_signals(df, adx_threshold=20.0)

        latest = df.iloc[-1]
        latest_dict = latest.to_dict()
        latest_bar = {k: (float(v) if pd.notna(v) else None) for k, v in latest_dict.items()}
        current_time = datetime.utcnow().isoformat() + "Z"

        # ポジション保有中の場合、エグジット条件をチェック
        if portfolio.current_position:
            exit_price = check_exit(portfolio.current_position, latest_bar, atr_multiplier=1.5)
            if exit_price is not None:
                portfolio.close_position(exit_price, current_time, reason="stop")
                print(f"[{current_time}] Position closed at ${exit_price:.2f} (stop)")

            # 利益確定条件（+2.5%）
            elif portfolio.current_position.direction == "long":
                if latest['close'] >= portfolio.current_position.entry_price * 1.025:
                    portfolio.close_position(float(latest['close']), current_time, reason="target")
                    print(f"[{current_time}] Position closed at ${latest['close']:.2f} (target)")

        # ポジションがない場合、エントリーシグナルをチェック
        if not portfolio.current_position and portfolio.get_total_trades() < 15:
            signal = latest.get('entry_signal')
            if pd.notna(signal):
                direction = signal
                position = open_position(-1, latest_bar, direction, atr_multiplier=1.5)

                quantity = portfolio.get_equity() * 0.10 / position.entry_price
                if quantity > 0:
                    portfolio.open_position(position, current_time, "BTC/USDT", quantity, latest_bar)
                    print(f"[{current_time}] Position opened: {direction.upper()} @ ${position.entry_price:.2f}")
                    print(f"  SL: ${position.stop_price:.2f} | Target: ${position.target_price:.2f}")

        # ポートフォリオをJSON保存
        portfolio.save_to_json(portfolio_file)

        # チャートデータを取得・保存
        chart_data = get_chart_data(exchange)
        if chart_data:
            with open(chart_file, 'w') as f:
                json.dump(chart_data, f, indent=2)

        # ダッシュボードを生成
        generate_dashboard(portfolio_file, chart_file)

        # 状態をgitに永続化（リモートルーティン実行間で履歴を保持するため）
        persist_state_to_git([
            portfolio_file,
            chart_file,
            "reports/paper_trading_dashboard.html",
        ])

        # 統計を出力
        status = "OPEN" if portfolio.current_position else "CLOSED"
        timestamp = datetime.utcnow().isoformat() + "Z"
        print(f"\n=== Paper Trading Status [{timestamp}] ===")
        print(f"Position: {status}")
        if portfolio.current_position:
            print(f"  Entry: ${portfolio.current_position.entry_price:.2f} ({portfolio.current_position.direction.upper()})")
            print(f"  SL: ${portfolio.current_position.stop_price:.2f}")
        print(f"Equity: ${portfolio.get_equity():,.2f}")
        print(f"Total PnL: ${portfolio.get_pnl():,.2f}")
        print(f"Total Trades: {portfolio.get_total_trades()}")
        print(f"Win Rate: {portfolio.get_win_rate():.1%}" if portfolio.get_total_trades() > 0 else "")
        print(f"========================================\n")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_daily_paper_trading()
