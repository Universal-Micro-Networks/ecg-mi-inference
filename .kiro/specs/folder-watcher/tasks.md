# タスク一覧: フォルダ監視機能 (folder-watcher)

## Backend

- [x] `FolderWatcherService` を実装
  - [x] 絶対パス・ネットワークマウント向けの `MFER_WATCH_FOLDER` 解決（`resolve` 失敗時のフォールバック）
  - [x] `MFER_WATCH_USE_POLLING` / `MFER_WATCH_POLLING_INTERVAL_SEC` による `PollingObserver` 切替
  - [x] `/health` 用 snapshot に `use_polling_observer` を含める
  - [x] Watchdog 監視開始/停止
  - [x] `.mwf/.MWF` 判定
  - [x] 書き込み完了待機
  - [x] 非同期 importer 呼び出し
  - [x] 重複防止（in_progress + LRU）
  - [x] 定期統計ログ

- [x] `file-importer` 連携境界を追加
  - [x] `import_mfer_file(file_path)` の呼び出しポイントを作成

- [x] FastAPI 起動/終了連携
  - [x] lifespan で watcher start/stop
  - [x] `/health` に watcher 状態を追加

- [x] 依存関係追加
  - [x] `watchdog` を backend 依存へ追加

## テスト

- [x] 非 MFER を無視するテスト
- [x] `.mwf` 検出で importer が呼ばれるテスト
- [x] 監視フォルダ未作成時はブートストラップが待機し、作成後に `PollingObserver` で既存 `.mwf` を取り込む統合テスト
- [x] 定期統計 INFO ログの `detected/success/failed/active` が `snapshot()` と一致することの検証

`file-importer` 本実装との接続は `main.py` の lifespan で `FolderWatcherService(importer_func=import_mfer_file)` により接続済み。
