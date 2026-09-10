# Pinterest×AIアフィリエイト自動化パイプライン — 初期セットアップ

このセットアップは人間が一度だけ行う。完了後の日次実行は `docs/DAILY_RUN_PROMPT.md` に沿って CronCreate による自動実行に委ねる。

## 1. Pinterest API

1. https://developers.pinterest.com/ でアプリを登録し、API アクセストークンを取得する（Trial / スコープ: `pins:write`, `boards:read`, `pins:read`）。
2. `.env` の `PINTEREST_ACCESS_TOKEN` に設定する。
3. 日本語用ボード・英語用ボードをそれぞれ作成し、`python3 -m src.main --help` の `--boards` に渡すボードIDを、`python3 -c "from src.pinterest_client import PinterestClient; print(PinterestClient().list_boards())"` などで取得して控えておく。
4. Pinterest API v5仕様（`media_source.source_type: "image_base64"` によるダイレクトアップロード）は実装時点の最新仕様と差異がないか、初回セットアップ時に実際のAPIレスポンスで確認すること。差異があれば `src/pinterest_client.py` を更新する。

## 2. A8.net（既存アカウント）

1. カメラ/写真機材ジャンルの広告案件を審査申請する。
2. 承認された案件のアフィリエイトリンクを `data/catalog.json` の各商品の `a8net_link` に設定する。

## 3. 海外ASP

1. Amazon Associates（US）など、海外向けASPに新規登録する。
2. 承認された案件のアフィリエイトリンクを `data/catalog.json` の `overseas_link.url` に設定する。
3. どのASPを採用するかは登録時の審査状況に応じて決めてよい（設計書で確定済みの前提はない）。

## 4. 商品カタログ作成

1. `data/catalog.example.json` を `data/catalog.json` にコピーする。
2. 実際の商品名・リンクに置き換える（`REPLACE_WITH_*` プレースホルダーをすべて置換）。

## 5. Gemini API

1. `GEMINI_API_KEY`（`stock-photo-tagger` スキルで使用しているものを流用可）を `.env` に設定する。

## 6. Discord通知（任意）

1. `DISCORD_WEBHOOK_URL`（freee-accounting-automationで使用しているものを流用するか、新規にWebhook URLを発行）を `.env` に設定する。
2. 未設定の場合、エラー時通知は送信されないだけで、パイプライン自体は動作する。

## 7. 日次実行の自動化

1. `docs/DAILY_RUN_PROMPT.md` の手順を確認する。
2. CronCreateツールでこのランブックの内容を日次実行として登録する（実行時刻はオーナーの都合の良い時間、例: 毎日09:00 JST）。

## 8. 依存関係のインストール

```bash
cd pinterest-affiliate-automation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
