# Pinterest×AIアフィリエイト自動化パイプライン

カメラ/写真機材のアフィリエイト商品を、日本語（A8.net）・英語（海外ASP）両ボードにPinterest経由で日次自動投稿するパイプライン。

## 構成

- `src/` — 決定的でテスト可能なライブラリ層（カタログ選定・安全性チェック・コピー生成・Pinterest投稿・ログ・通知・オーケストレーション）
- `tests/` — pytestによる単体テスト（すべてモック、外部APIは呼ばない）
- `docs/SETUP.md` — 初期セットアップ手順（人間が一度だけ実施）
- `docs/DAILY_RUN_PROMPT.md` — 日次実行ランブック（CronCreateから起動されるClaude Codeエージェント用。nanobananaでの画像生成を担当）
- `data/catalog.example.json` — 商品カタログのサンプル（`data/catalog.json` にコピーして実データに置換する）

## セットアップ

`docs/SETUP.md` を参照。

## テスト実行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest
```
