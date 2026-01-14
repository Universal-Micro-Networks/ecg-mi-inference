# 設計ドキュメント: フォルダ監視機能 (folder-watcher)

## 概要

**目的**: 本機能は、指定フォルダを監視し、新規MFERファイル（.mwf/.MWF）の追加を検出し、
`file-importer` サービスを呼び出すバックグラウンドサービスである。

**ユーザー**: システム管理者が監視対象フォルダを設定し、サービスを起動・停止する。

**特徴**: Watchdogライブラリによるファイルシステムイベント監視、書き込み完了待機、
重複検出防止、非同期処理によるfile-importer呼び出しを実現する。

### ゴール

- Watchdogによるファイルシステムイベント監視の実装
- MFERファイル検出と拡張子判定
- ファイル書き込み完了の待機（サイズ監視）
- file-importerへの非同期呼び出し（同時実行数制限）
- 重複処理の防止（LRU方式）
- ヘルスチェックエンドポイントによる監視状態の確認

### 非ゴール

- MFERファイルの解析・DB登録（file-importerの責務）
- 心電図波形データの処理（ecg-mi-inferencerの責務）
- ファイルの移動・削除（file-importerの責務）
- ユーザーインターフェース（バックグラウンドサービス）

## アーキテクチャ

### アーキテクチャパターン

**選択パターン**: Layered Architecture（Backend）

**ドメイン境界**:
- `app/api/` にヘルスチェックエンドポイント（Presentation層）
- `app/services/` にフォルダ監視サービス（Application層）
- `app/domain/` に監視状態・統計のドメインモデル（Domain層）
- `app/infrastructure/` にWatchdog統合、file-importer呼び出し（Infrastructure層）

**ステアリング準拠**:
- DDD原則に従い、ドメイン層は外部依存なし
- Layered Architectureで責務分離

### システム境界図

```mermaid
graph TB
    subgraph FW["folder-watcher（本機能）"]
        direction TB

        subgraph Presentation["Presentation Layer"]
            HealthAPI["HealthRouter<br/>/health"]
        end

        subgraph Application["Application Layer"]
            WatchService["FolderWatchService<br/>監視管理"]
            StatsCollector["StatisticsCollector<br/>統計収集"]
        end

        subgraph Domain["Domain Layer"]
            WatchState["WatchState<br/>監視状態"]
            FileStats["FileStatistics<br/>統計情報"]
        end

        subgraph Infrastructure["Infrastructure Layer"]
            WatchdogHandler["WatchdogEventHandler<br/>イベントハンドラ"]
            FileWatcher["FileWatcher<br/>Watchdog統合"]
            WriteWait["WriteCompletionWaiter<br/>書き込み完了待機"]
            DuplicateTracker["DuplicateTracker<br/>重複追跡（LRU）"]
            ImporterClient["FileImporterClient<br/>HTTP Client"]
        end
    end

    subgraph External["外部サービス"]
        FileImporter["file-importer<br/>HTTP API"]
        FileSystem["ファイルシステム<br/>監視対象フォルダ"]
    end

    HealthAPI --> WatchService
    WatchService --> WatchState
    WatchService --> WatchdogHandler
    WatchService --> StatsCollector
    StatsCollector --> FileStats
    WatchdogHandler --> WriteWait
    WatchdogHandler --> DuplicateTracker
    WatchdogHandler --> ImporterClient
    WatchdogHandler --> FileWatcher
    FileWatcher --> FileSystem
    ImporterClient -->|HTTP POST| FileImporter
```

### 技術スタック

| Layer | 選択技術 | 役割 | 備考 |
|-------|----------|------|------|
| Backend | FastAPI + Python 3.14+ | ヘルスチェックAPI、サービス管理 | |
| ファイル監視 | Watchdog | ファイルシステムイベント監視 | |
| 非同期処理 | asyncio + aiohttp | file-importer呼び出し | |
| ログ | Python logging | ログ出力 | |
| シグナル処理 | signal | SIGTERM/SIGINTハンドリング | |

## システムフロー

### ファイル検出・処理フロー

```mermaid
sequenceDiagram
    participant FS as ファイルシステム
    participant Watchdog as WatchdogHandler
    participant WriteWait as WriteCompletionWaiter
    participant Duplicate as DuplicateTracker
    participant Service as FolderWatchService
    participant Client as FileImporterClient
    participant Importer as file-importer

    FS->>Watchdog: ファイル作成イベント
    Watchdog->>Watchdog: 拡張子判定（.mwf/.MWF）

    alt 拡張子がMFER形式
        Watchdog->>Duplicate: 重複チェック

        alt 重複なし
            Watchdog->>WriteWait: 書き込み完了待機開始
            WriteWait->>WriteWait: ファイルサイズ監視（2秒間隔）

            loop ファイルサイズが変化中
                WriteWait->>FS: ファイルサイズ取得
                FS-->>WriteWait: サイズ情報
            end

            WriteWait-->>Watchdog: 書き込み完了

            Watchdog->>Service: 処理リクエスト
            Service->>Client: file-importer呼び出し（非同期）
            Client->>Importer: HTTP POST /api/import (ファイルパス)
            Importer-->>Client: HTTP 200/400/500
            Client-->>Service: 結果（成功/失敗）
            Service->>Service: 統計更新
            Service->>Duplicate: 処理済みとして記録

        else 重複あり
            Watchdog->>Watchdog: スキップ（DEBUGログ）
        end
    else 拡張子がMFER形式でない
        Watchdog->>Watchdog: 無視（DEBUGログ）
    end
```

### サービス起動フロー

```mermaid
sequenceDiagram
    participant System as システム起動
    participant Service as FolderWatchService
    participant Watchdog as FileWatcher
    participant FS as ファイルシステム
    participant HealthAPI as HealthRouter

    System->>Service: 初期化
    Service->>Service: 環境変数読み込み
    Service->>FS: 監視対象フォルダ存在確認

    alt フォルダが存在しない
        Service->>Service: エラーログ出力
        Service->>Service: ポーリング開始（1分間隔）

        loop フォルダが作成されるまで
            Service->>FS: フォルダ存在確認
            FS-->>Service: 存在しない
        end

        FS-->>Service: フォルダ作成検出
    end

    Service->>Watchdog: 監視開始（監視対象フォルダ）
    Watchdog->>FS: 監視登録
    Watchdog-->>Service: 監視開始完了
    Service->>Service: 状態を「稼働中」に更新
    Service->>HealthAPI: ヘルスチェック有効化
    Service->>Service: INFOログ「監視開始」
```

### サービス停止フロー

```mermaid
sequenceDiagram
    participant Signal as SIGTERM/SIGINT
    participant Service as FolderWatchService
    participant Watchdog as FileWatcher
    participant Client as FileImporterClient
    participant HealthAPI as HealthRouter

    Signal->>Service: シグナル受信
    Service->>Service: 状態を「停止中」に更新
    Service->>HealthAPI: ヘルスチェック無効化（HTTP 503）
    Service->>Watchdog: 監視停止
    Watchdog-->>Service: 停止完了

    Service->>Client: 進行中タスクの完了待機

    alt タイムアウト（30秒）内に完了
        Client-->>Service: 全タスク完了
        Service->>Service: INFOログ「監視停止」
        Service->>System: 正常終了（exit 0）
    else タイムアウト
        Service->>Service: 警告ログ「タイムアウト」
        Service->>System: 強制終了（exit 1）
    end
```

## コンポーネント設計

### 1. FolderWatchService（Application層）

**責務**: フォルダ監視サービスのライフサイクル管理、状態管理、統計収集

**主要メソッド**:

```python
class FolderWatchService:
    async def start(self) -> None:
        """監視を開始する"""

    async def stop(self, timeout: int = 30) -> None:
        """監視を停止する（タイムアウト付き）"""

    def get_state(self) -> WatchState:
        """現在の監視状態を取得する"""

    def get_statistics(self) -> FileStatistics:
        """統計情報を取得する"""
```

**依存関係**:
- `WatchdogEventHandler`（Infrastructure層）
- `StatisticsCollector`（Application層）
- `WatchState`（Domain層）

### 2. WatchdogEventHandler（Infrastructure層）

**責務**: Watchdogイベントの処理、拡張子判定、書き込み完了待機のトリガー

**主要メソッド**:

```python
class WatchdogEventHandler(FileSystemEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        """ファイル作成イベントを処理する"""

    def _is_mfer_file(self, file_path: str) -> bool:
        """拡張子がMFER形式（.mwf/.MWF）か判定する"""

    async def _wait_for_write_completion(
        self, file_path: str
    ) -> bool:
        """ファイル書き込み完了を待機する"""
```

**依存関係**:
- `WriteCompletionWaiter`（Infrastructure層）
- `DuplicateTracker`（Infrastructure層）
- `FileImporterClient`（Infrastructure層）

### 3. WriteCompletionWaiter（Infrastructure層）

**責務**: ファイルサイズの変化を監視し、書き込み完了を判定する

**主要メソッド**:

```python
class WriteCompletionWaiter:
    async def wait_for_completion(
        self, file_path: str, wait_interval: int = 2, timeout: int = 60
    ) -> bool:
        """ファイル書き込み完了を待機する

        Returns:
            True: 書き込み完了、False: タイムアウト
        """
```

### 4. DuplicateTracker（Infrastructure層）

**責務**: 処理中・処理済みファイルの追跡、LRU方式でのメモリ管理

**主要メソッド**:

```python
class DuplicateTracker:
    def is_duplicate(self, file_path: str) -> bool:
        """重複チェック"""

    def mark_processing(self, file_path: str) -> None:
        """処理中として記録"""

    def mark_completed(self, file_path: str) -> None:
        """処理完了として記録"""

    def _evict_oldest(self) -> None:
        """最も古いエントリを削除（LRU）"""
```

**実装**: `collections.OrderedDict`を使用し、LRU方式を実現

### 5. FileImporterClient（Infrastructure層）

**責務**: file-importer HTTP APIへの非同期呼び出し、同時実行数制限

**主要メソッド**:

```python
class FileImporterClient:
    async def import_file(self, file_path: str) -> ImportResult:
        """file-importerを呼び出す

        Returns:
            ImportResult(success: bool, message: str)
        """

    async def _call_importer_api(self, file_path: str) -> Response:
        """HTTP API呼び出し（POST /api/import）"""
```

**実装**: `aiohttp.ClientSession` + `asyncio.Semaphore`で同時実行数制限

### 6. StatisticsCollector（Application層）

**責務**: 統計情報の収集・集計

**主要メソッド**:

```python
class StatisticsCollector:
    def record_file_detected(self) -> None:
        """ファイル検出を記録"""

    def record_import_success(self) -> None:
        """インポート成功を記録"""

    def record_import_failure(self) -> None:
        """インポート失敗を記録"""

    def get_statistics(self) -> FileStatistics:
        """統計情報を取得"""
```

### 7. HealthRouter（Presentation層）

**責務**: ヘルスチェックエンドポイントの提供

**主要メソッド**:

```python
@router.get("/health")
async def health_check(
    service: FolderWatchService = Depends(get_watch_service)
) -> HealthResponse:
    """ヘルスチェックエンドポイント

    Returns:
        HTTP 200: 正常稼働中
        HTTP 503: 停止中または異常
    """
```

## データモデル

### WatchState（Domain層）

```python
@dataclass
class WatchState:
    """監視状態"""
    status: WatchStatus  # RUNNING, STOPPING, STOPPED
    watch_folder: str
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    last_detected_at: Optional[datetime]
```

### FileStatistics（Domain層）

```python
@dataclass
class FileStatistics:
    """ファイル処理統計"""
    total_detected: int  # 検出ファイル数
    total_imported: int  # インポート成功数
    total_failed: int  # インポート失敗数
    current_processing: int  # 現在処理中数
    last_updated_at: datetime
```

### ImportResult（Infrastructure層）

```python
@dataclass
class ImportResult:
    """file-importer呼び出し結果"""
    success: bool
    message: str
    status_code: Optional[int] = None
```

## エラーハンドリング

### エラー種別

| エラー種別 | 処理 | ログレベル |
|-----------|------|----------|
| 監視対象フォルダが存在しない | ポーリング継続 | ERROR |
| ファイル読み取りエラー | ファイルをスキップ | WARNING |
| 書き込み完了待機タイムアウト | ファイルをスキップ | WARNING |
| file-importer呼び出しエラー | エラーログ出力、統計更新 | ERROR |
| 重複検出 | スキップ（ログなし） | DEBUG |

### エラーハンドリングフロー

```mermaid
flowchart TD
    Error[エラー発生] --> CheckType{エラー種別}

    CheckType -->|監視対象フォルダなし| Poll[ポーリング継続<br/>ERRORログ]
    CheckType -->|ファイル読み取りエラー| Skip1[ファイルスキップ<br/>WARNINGログ]
    CheckType -->|書き込みタイムアウト| Skip2[ファイルスキップ<br/>WARNINGログ]
    CheckType -->|file-importerエラー| Log[エラーログ出力<br/>統計更新<br/>ERRORログ]
    CheckType -->|重複検出| Debug[スキップ<br/>DEBUGログ]

    Poll --> Continue[処理継続]
    Skip1 --> Continue
    Skip2 --> Continue
    Log --> Continue
    Debug --> Continue
```

## テスト戦略

### 単体テスト（Unit Tests）

**対象**: 各コンポーネントの個別テスト

| コンポーネント | テスト内容 |
|--------------|----------|
| `WatchdogEventHandler` | 拡張子判定、イベント処理 |
| `WriteCompletionWaiter` | 書き込み完了判定、タイムアウト |
| `DuplicateTracker` | 重複検出、LRU削除 |
| `FileImporterClient` | HTTP呼び出し、同時実行数制限 |
| `StatisticsCollector` | 統計収集・集計 |

**テストツール**: pytest, pytest-asyncio, pytest-mock

### 統合テスト（Integration Tests）

**対象**: コンポーネント間の連携テスト

- Watchdog → EventHandler → FileImporterClient の連携
- 実際のファイルシステムを使用したファイル検出テスト
- file-importerモックを使用した呼び出しテスト

**テストツール**: pytest, aioresponses（HTTPモック）

### E2Eテスト（End-to-End Tests）

**対象**: 実際の環境での動作確認

- 監視対象フォルダにMFERファイルを配置
- ファイル検出からfile-importer呼び出しまでの全フロー確認
- ヘルスチェックエンドポイントの動作確認

### カバレッジ目標

- **Backend**: 80% 以上

## デプロイメント/インストールノート

### 開発環境（Docker Compose）

```yaml
# docker-compose.yml
services:
  folder-watcher:
    build: ./backend
    environment:
      - MFER_WATCH_FOLDER=/data/mfer
      - MFER_WATCH_RECURSIVE=true
      - MFER_MAX_CONCURRENT=5
      - MFER_HEALTH_PORT=8081
      - FILE_IMPORTER_URL=http://file-importer:8000
    volumes:
      - ./data/mfer:/data/mfer:ro
    command: python -m app.services.folder_watcher
```

### 本番環境（ローカルインストール）

**依存パッケージ**:
```bash
pip install fastapi uvicorn watchdog aiohttp
```

**起動コマンド**:
```bash
export MFER_WATCH_FOLDER=/path/to/watch
export FILE_IMPORTER_URL=http://localhost:8000
python -m app.services.folder_watcher
```

**systemdサービス例**:
```ini
[Unit]
Description=Folder Watcher Service
After=network.target

[Service]
Type=simple
User=ecg-user
WorkingDirectory=/opt/ecg-mi-inference/backend
Environment="MFER_WATCH_FOLDER=/data/mfer"
Environment="FILE_IMPORTER_URL=http://localhost:8000"
ExecStart=/usr/bin/python3 -m app.services.folder_watcher
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 設定要件

- 監視対象フォルダへの読み取り権限
- file-importerサービスへのネットワークアクセス
- ヘルスチェックポート（デフォルト: 8081）の開放

---

**ステータス:** レビュー待ち
**作成日:** 2025-12-07
**最終更新:** 2025-12-07



