# Pinterest日次自動投稿 ランブック（CronCreateから起動されるClaude Codeエージェント用）

## 前提
- 作業ディレクトリ: `pinterest-affiliate-automation/`
- `.env` に `GEMINI_API_KEY` / `PINTEREST_ACCESS_TOKEN` / `DISCORD_WEBHOOK_URL` が設定済み
- `data/catalog.json` が作成済み（`docs/SETUP.md` 参照）

## 手順

1. 今日の日付で、本日対象の商品IDを確認する:
   ```bash
   python3 -c "from datetime import date; from src.catalog import ProductCatalog; c = ProductCatalog('data/catalog.json'); print([p['id'] for p in c.pick_for_date(date.today(), 3)])"
   ```

2. 画像保存先ディレクトリ（`/tmp/pinterest-images/<今日の日付>/`）を作成する。

3. 対象商品ごとに、nanobanana（`mcp__nanobanana__generate_image`）でJP用・EN用の画像を1枚ずつ生成する。
   - 商品カテゴリに合った、Pinterestで映えるライフスタイル/プロダクト写真調のプロンプトを使う。
   - 生成した画像を必ず目視確認し、以下を満たさない場合は再生成する（テキストの安全性チェックとは別に、エージェントが判断する）:
     - 実在ブランドのロゴ・商標が写り込んでいないこと
     - 誤解を招く誇張表現（過度な演出・捏造的な効果）がないこと
     - Pinterestのコンテンツポリシーに抵触しないこと
   - 生成画像を `<product_id>_ja.jpg` / `<product_id>_en.jpg` として画像保存先ディレクトリに保存する。

4. 以下を実行してパイプラインを起動する（`--boards` は実際のPinterestボードIDに置き換える）:
   ```bash
   cd pinterest-affiliate-automation
   python3 -m src.main \
     --images-dir /tmp/pinterest-images/$(date +%Y-%m-%d) \
     --boards <ja_board_id>:<en_board_id> \
     --count 3
   ```

5. 実行結果を確認する。エラー・安全性チェック最終失敗があった場合はDiscordに通知が飛ぶ。正常終了時は通知しない。

## CronCreate登録（初回のみ、人間が実行）

`docs/SETUP.md` の初期セットアップ完了後、CronCreateツールでこのランブックの内容を日次実行として登録する（実行時刻はオーナーの都合の良い時間、例: 毎日09:00 JST）。

## 備考

nanobananaでの画像生成・目視確認はエージェント判断が必要な処理のため、単体テスト対象外である。決定的な部分（カタログ選定・安全性チェック・コピー生成・Pinterest投稿・ログ・通知）は `src/` 配下のモジュールとしてすべてpytestでテスト済み。
