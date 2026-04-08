# 設計ドキュメント: フォルダ監視機能 (folder-watcher)

## 概要

`folder-watcher` は `MFER_WATCH_FOLDER` を監視し、新規 `.mwf/.MWF` ファイルを検出して `file-importer` 呼び出しに渡す。
本実装はバックエンドプロセス内の常駐サービスとして起動し、停止時は進行中タスクを待機して終了する。

## アーキテクチャ

- **Watcher Engine**: Watchdog `Observer`（既定）または `PollingObserver`（`MFER_WATCH_USE_POLLING`）+ `FileSystemEventHandler`
- **Dispatch**: `ThreadPoolExecutor` による非同期 importer 呼び出し
- **Duplicate Guard**: `in_progress` + LRU (`OrderedDict`) で重複処理防止
- **Completion Wait**: ファイルサイズ安定を確認してから importer 実行
- **Health**: `/health` に監視状態と統計を含めて返却

## 主要コンポーネント

### `MFER_WATCH_FOLDER` の解決

- **絶対パス**: `Path.expanduser()` 後に `resolve(strict=False)`。`OSError` / `RuntimeError` 時は警告ログのうえ指定パスをそのまま使用（一時的なマウント切れや一部ネットワークパスでの正規化失敗に備える）。
- **相対パス**: カレントディレクトリ基準で `resolve()` し、存在すれば採用。無ければリポジトリルート（`docker-compose.yml` がある階層）基準で存在チェック。

### Observer の選択

- `MFER_WATCH_USE_POLLING` が真のとき `watchdog.observers.polling.PollingObserver(timeout=...)`。間隔は `MFER_WATCH_POLLING_INTERVAL_SEC`（秒、既定 1）。
- 偽のとき従来どおり `watchdog.observers.Observer`（OS ネイティブバックエンド）。

### `backend/app/folder_watcher.py`

- `FolderWatcherService.start()`
  - ブートストラップスレッドで `watch_folder.exists()` が真になるまで約 2 秒間隔で待機（未存在時は ERROR ログ）。メインスレッド（lifespan）をブロックしない
  - フォルダ出現後に Watchdog 起動（上記ルールで Observer を選択）、既存 `.mwf` を列挙して enqueue
  - 定期統計ログスレッド起動（`MFER_STATS_INTERVAL` 秒ごとに INFO: `folder-watcher stats: detected=…`）
- `FolderWatcherService.enqueue_if_target(path)`
  - `.mwf/.MWF` 拡張子判定
  - 重複検知
  - 非同期キュー投入
- `FolderWatcherService._wait_write_complete(path)`
  - サイズ不変を `MFER_WRITE_WAIT_INTERVAL` 間隔で監視
  - `MFER_WRITE_TIMEOUT` 超過時はスキップ
- `FolderWatcherService.stop()`
  - Observer 停止
  - 進行中処理を `MFER_SHUTDOWN_TIMEOUT` まで待機

### `backend/app/file_importer.py`

- `import_mfer_file(file_path: str)`
  - `file-importer` のエントリ。`folder-watcher` は検出した絶対パスをこの関数に渡す（`main.py` で注入）

### `backend/app/main.py`

- FastAPI lifespan で watcher start/stop
- `/health` に `folder_watcher` 状態を含める
- watcher 異常時は 503 を返す

## データ/状態

- **in_progress**: 処理中パス集合
- **tracked (LRU)**: 処理済み追跡（上限 `MFER_TRACKING_LIMIT`）
- **stats / snapshot**:
  - detected / success / failed / active_tasks / last_detected_at / watching / bootstrap_pending / use_polling_observer

## エラーハンドリング

- 監視フォルダ未存在: ERROR ログ + リトライ
- 非 MFER ファイル: DEBUG ログで無視
- 書き込み完了待機タイムアウト: WARNING ログでスキップ
- importer 失敗: ERROR ログ + 失敗件数加算

## 設定（環境変数）

- `MFER_WATCH_FOLDER` (required)
- `MFER_WATCH_USE_POLLING` (default: false)
- `MFER_WATCH_POLLING_INTERVAL_SEC` (default: 1)
- `MFER_WATCH_RECURSIVE` (default: true)
- `MFER_MAX_CONCURRENT` (default: 5)
- `MFER_WRITE_WAIT_INTERVAL` (default: 2)
- `MFER_WRITE_TIMEOUT` (default: 60)
- `MFER_SHUTDOWN_TIMEOUT` (default: 30)
- `MFER_TRACKING_LIMIT` (default: 10000)
- `MFER_STATS_INTERVAL` (default: 300)

## テスト戦略

- 単体:
  - 拡張子フィルタ
  - 重複検知
  - enqueue 後の importer 呼び出し
  - 絶対パス解決、`use_polling_observer` を snapshot が反映すること
- 統合:
  - 監視対象に `.mwf` 作成 -> importer 呼び出し
  - 非対象拡張子が無視される
  - 監視パスが未作成の状態で `start()` → `bootstrap_pending`・ERROR「Watch folder not found」後にディレクトリ作成 → `PollingObserver` で起動し既存 `.mwf` を取り込む（`test_bootstrap_waits_until_watch_folder_exists_polling_observer`）
  - 短い `MFER_STATS_INTERVAL` で定期 INFO ログの `detected/success/failed/active` が `snapshot()` と一致すること（`test_periodic_stats_log_matches_snapshot_counters`）
