# タスク一覧: ファイルインポート機能 (file-importer)

## 1. 入口とバリデーション

- [x] `backend/app/file_importer.py` のエントリ関数を本実装化
  - [x] 入力パス存在チェック
  - [x] 読み取り権限チェック
  - [x] 拡張子判定（`.mwf` を大文字小文字無視）

## 2. 解析処理

- [x] `mfer_tools.extract_mfer_header()` を利用したヘッダ抽出を実装
  - [x] `MWF_TIM` から検査日時を抽出
  - [x] 患者ID/氏名/性別/生年月日のキー候補をマッピング
- [x] XMLフォールバックパーサを実装
  - [x] MWF同名XMLから患者属性・検査日時を補完
  - [x] AKASHIサンプル互換形式で抽出確認

## 3. DB登録

- [x] 患者 upsert 相当を実装（`external_id` 基準）
- [x] 診察重複判定を実装（`patient_id + exam_date`）
- [x] 診察レコード作成時に以下を設定
  - [x] MFERの絶対パスを保持（現スキーマでは `notes` と `csv_file_path` に格納）
  - [x] `inference_status='未実行'` 相当（`Inference` 初期レコード作成）
- [x] 登録処理を単一トランザクション化

## 4. ファイル移動とエラー処理

- [x] `MFER_PROCESSED_FOLDER` / `MFER_ERROR_FOLDER` を実装
- [x] 成功時 processed へ移動、失敗時 error へ移動
- [x] 移動後パスで診察レコード更新
- [x] エラー分類と終了コード（0/1）を統一

## 5. テスト

- [x] 単体テスト
  - [x] 拡張子判定（`.mwf/.MWF`）
  - [x] ヘッダ抽出マッピング
  - [x] XMLフォールバック抽出
- [x] 統合テスト
  - [x] sample_data互換ケース 1件インポート成功
  - [x] 重複ファイル再投入でスキップ
  - [x] 不正ファイルでエラー遷移

## 6. 運用/ドキュメント

- [x] 必須環境変数・デフォルト値を README/DOCKER.md に追記
- [x] folder-watcher とのインターフェース（入力/戻り値/例外）を明文化
