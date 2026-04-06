# タスク一覧: フォルダ監視機能 (folder-watcher)

## Backend

- [x] `FolderWatcherService` を実装
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

## 残課題

- [ ] file-importer 本実装との接続（現在はプレースホルダ）
- [ ] 監視フォルダ未存在時のポーリング挙動を統合テスト化
- [ ] 稼働統計ログ内容の詳細検証
