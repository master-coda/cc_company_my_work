import json
from datetime import datetime


def generate_dashboard(portfolio_file: str, output_file: str = "reports/paper_trading_dashboard.html") -> None:
    """ペーパートレーディングダッシュボードを生成"""
    with open(portfolio_file, 'r') as f:
        portfolio = json.load(f)

    initial_capital = portfolio["initial_capital"]
    current_equity = portfolio["current_equity"]
    total_pnl = portfolio["total_pnl"]
    total_trades = portfolio["total_trades"]
    win_rate = portfolio["win_rate"]
    trades = portfolio["trades"]

    pnl_percent = (total_pnl / initial_capital) * 100

    trade_rows = ""
    for i, trade in enumerate(trades, 1):
        pnl_color = "green" if trade["pnl"] > 0 else "red"
        trade_rows += f"""
        <tr>
            <td>{i}</td>
            <td>{trade['timestamp']}</td>
            <td>{trade['symbol']}</td>
            <td>${trade['entry_price']:.2f}</td>
            <td>${trade['exit_price']:.2f}</td>
            <td>{trade['quantity']:.4f}</td>
            <td style="color: {pnl_color}; font-weight: bold;">${trade['pnl']:.2f}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Paper Trading Dashboard - Trend Following</title>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .metric {{
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
                border-left: 4px solid #007bff;
            }}
            .metric-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-top: 5px;
            }}
            .positive {{ color: #28a745; }}
            .negative {{ color: #dc3545; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #007bff;
                color: white;
                padding: 10px;
                text-align: left;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f9f9f9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Paper Trading Dashboard - Trend Following</h1>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Initial Capital</div>
                    <div class="metric-value">${initial_capital:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Current Equity</div>
                    <div class="metric-value">${current_equity:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total PnL</div>
                    <div class="metric-value {'positive' if total_pnl >= 0 else 'negative'}">${total_pnl:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">PnL %</div>
                    <div class="metric-value {'positive' if pnl_percent >= 0 else 'negative'}">{pnl_percent:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{total_trades}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{win_rate:.1%}</div>
                </div>
            </div>

            <h2>Trade History</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Timestamp</th>
                    <th>Symbol</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Quantity</th>
                    <th>PnL</th>
                </tr>
                {trade_rows if trade_rows else '<tr><td colspan="7" style="text-align: center; color: #999;">No trades yet</td></tr>'}
            </table>

            <div style="margin-top: 30px; font-size: 12px; color: #999; text-align: right;">
                Generated: {datetime.utcnow().isoformat()}Z
                <br>
                Simulating Trend Following Strategy with Initial Capital ${initial_capital:,.2f}
            </div>
        </div>
    </body>
    </html>
    """

    with open(output_file, 'w') as f:
        f.write(html_content)

    print(f"Dashboard generated: {output_file}")
