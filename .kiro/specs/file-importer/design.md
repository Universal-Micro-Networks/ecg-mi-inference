# 設計ドキュメント: ファイルインポート機能 (file-importer)

## 概要

**目的**: 本機能は、`folder-watcher` から呼び出され、MFERファイルから患者属性を抽出し、
患者データおよび検査データ（検索用メタデータ）をデータベースに登録するサービスである。

**ユーザー**: `folder-watcher` サービスが自動的に呼び出す。また、システム管理者が手動でCLI経由で呼び出すことも可能。

**特徴**: MFERファイルから患者属性のみを抽出（波形データは読み込まない）、
トランザクション管理による整合性保証、処理済みファイルの自動移動を実現する。

### ゴール

- MFERファイルからの患者属性抽出（患者ID、氏名、生年月日、性別、検査日時、検査種別）
- 患者データ・検査データのDB登録（重複チェック、既存患者の再利用）
- MFERファイルパスの検査レコードへの紐付け
- 処理済みファイルの移動（成功時: 処理済みフォルダ、失敗時: エラーフォルダ）
- HTTP API（FastAPI）およびCLIインターフェース

### 非ゴール

- 心電図波形データの読み込み（ecg-mi-inferencerの責務）
- CSV変換・画像変換（ecg-mi-inferencerの責務）
- 心筋梗塞リスク推論（ecg-mi-inferencerの責務）
- ファイル監視・検出（folder-watcherの責務）

## アーキテクチャ

### アーキテクチャパターン

**選択パターン**: Layered Architecture（Backend）

**ドメイン境界**:
- `app/api/v1/import.py` にインポートエンドポイント（Presentation層）
- `app/services/import_service.py` にインポートサービス（Application層）
- `app/domain/patient/`, `app/domain/examination/` にドメインモデル（Domain層）
- `app/infrastructure/mfer/` にMFERパーサー、`app/infrastructure/database/` にRepository実装（Infrastructure層）

**ステアリング準拠**:
- DDD原則に従い、ドメイン層は外部依存なし
- Layered Architectureで責務分離

### システム境界図

```mermaid
graph TB
    subgraph FI["file-importer（本機能）"]
        direction TB

        subgraph Presentation["Presentation Layer"]
            ImportAPI["ImportRouter<br/>POST /api/import"]
            CLI["CLI Entry Point<br/>python -m app.cli.import"]
        end

        subgraph Application["Application Layer"]
            ImportService["ImportService<br/>インポート処理オーケストレーション"]
        end

        subgraph Domain["Domain Layer"]
            PatientEntity["Patient Entity<br/>患者エンティティ"]
            ExaminationEntity["Examination Entity<br/>検査エンティティ"]
            PatientRepo["PatientRepository<br/>インターフェース"]
            ExamRepo["ExaminationRepository<br/>インターフェース"]
        end

        subgraph Infrastructure["Infrastructure Layer"]
            MFERParser["MFERParser<br/>MFERファイル解析"]
            PatientRepoImpl["PatientRepositoryImpl<br/>SQLAlchemy実装"]
            ExamRepoImpl["ExaminationRepositoryImpl<br/>SQLAlchemy実装"]
            FileMover["FileMover<br/>ファイル移動"]
            DBConnection["DatabaseConnection<br/>トランザクション管理"]
        end
    end

    subgraph External["外部"]
        FolderWatcher["folder-watcher<br/>HTTP POST"]
        FileSystem["ファイルシステム<br/>MFERファイル"]
        DB[(PostgreSQL)]
    end

    FolderWatcher --> ImportAPI
    CLI --> ImportService
    ImportAPI --> ImportService
    ImportService --> MFERParser
    ImportService --> PatientRepo
    ImportService --> ExamRepo
    ImportService --> FileMover
    ImportService --> DBConnection

    PatientRepo --> PatientRepoImpl
    ExamRepo --> ExamRepoImpl

    MFERParser --> FileSystem
    PatientRepoImpl --> DB
    ExamRepoImpl --> DB
    FileMover --> FileSystem
    DBConnection --> DB
```

### 技術スタック

| Layer | 選択技術 | 役割 | 備考 |
|-------|----------|------|------|
| Backend | FastAPI + Python 3.14+ | REST API、CLI | |
| MFER解析 | MFERパーサーライブラリ | MFERファイル解析 | 実装時に選択 |
| Database | SQLAlchemy + PostgreSQL | ORM、データ永続化 | |
| ファイル操作 | Python pathlib | ファイル移動 | |
| ログ | Python logging | ログ出力 | |
| バリデーション | Pydantic | データ検証 | |

## システムフロー

### インポート処理フロー（HTTP API）

```mermaid
sequenceDiagram
    participant Watcher as folder-watcher
    participant API as ImportRouter
    participant Service as ImportService
    participant Parser as MFERParser
    participant PRepo as PatientRepository
    participant ERepo as ExaminationRepository
    participant DB as Database (Transaction)
    participant Mover as FileMover

    Watcher->>API: HTTP POST /api/import<br/>{file_path: "/path/to/file.mwf"}
    API->>Service: import_file(file_path)

    Service->>Service: ファイル存在確認
    Service->>Parser: parse_patient_attributes(file_path)
    Parser->>Parser: MFERファイル読み込み
    Parser->>Parser: 患者属性抽出（波形データスキップ）
    Parser-->>Service: PatientAttributes, ExamMetadata

    Service->>Service: バリデーション（必須項目チェック）

    Service->>DB: トランザクション開始

    Service->>PRepo: find_by_external_id(external_id)
    PRepo->>DB: SELECT WHERE external_id = ...
    DB-->>PRepo: Patient or None
    PRepo-->>Service: Patient or None

    alt 患者が存在しない
        Service->>PRepo: create(patient_data)
        PRepo->>DB: INSERT INTO patients ...
        DB-->>PRepo: Patient (with UUID)
    end

    Service->>ERepo: find_duplicate(patient_id, exam_date)
    ERepo->>DB: SELECT WHERE patient_id = ... AND exam_date = ...
    DB-->>ERepo: Examination or None
    ERepo-->>Service: Examination or None

    alt 検査が重複しない
        Service->>ERepo: create(exam_data, patient_id, file_path)
        ERepo->>DB: INSERT INTO examinations ...
        DB-->>ERepo: Examination (with UUID)
    else 検査が重複
        Service->>Service: 警告ログ出力
        Service->>DB: ロールバック
        Service-->>API: 重複エラー（HTTP 409）
        API-->>Watcher: HTTP 409 Conflict
    end

    Service->>DB: コミット
    DB-->>Service: 成功

    Service->>Mover: move_to_processed(file_path)
    Mover->>FileSystem: ファイル移動
    Mover->>ERepo: update_file_path(exam_id, new_path)
    ERepo->>DB: UPDATE examinations SET mfer_file_path = ...
    DB-->>ERepo: 成功

    Service-->>API: ImportResult(success=True, exam_id=...)
    API-->>Watcher: HTTP 200 OK<br/>{exam_id: "uuid", status: "success"}
```

### エラー処理フロー

```mermaid
flowchart TD
    Start([インポート開始]) --> ValidateFile{ファイル存在?}
    ValidateFile -->|No| FileError[ファイルエラー<br/>ログ出力]
    ValidateFile -->|Yes| Parse[MFER解析]

    Parse --> ParseOK{解析成功?}
    ParseOK -->|No| ParseError[パースエラー<br/>ログ出力]
    ParseOK -->|Yes| ValidateData{バリデーション成功?}

    ValidateData -->|No| ValidationError[バリデーションエラー<br/>ログ出力]
    ValidateData -->|Yes| BeginTx[トランザクション開始]

    BeginTx --> Register{患者・検査登録}
    Register -->|DBエラー| DBError[DBエラー<br/>ロールバック<br/>ログ出力]
    Register -->|成功| Commit[コミット]

    Commit --> Move{ファイル移動}
    Move -->|IOエラー| IOError[IOエラー<br/>警告ログ<br/>DBは維持]
    Move -->|成功| Success([正常終了])

    FileError --> MoveToError[エラーフォルダへ移動]
    ParseError --> MoveToError
    ValidationError --> MoveToError
    DBError --> MoveToError
    MoveToError --> Failure([エラー終了: HTTP 400/500])
    IOError --> Success
```

## コンポーネント設計

### 1. ImportService（Application層）

**責務**: インポート処理のオーケストレーション、トランザクション管理

**主要メソッド**:

```python
class ImportService:
    async def import_file(self, file_path: str) -> ImportResult:
        """MFERファイルをインポートする

        Returns:
            ImportResult(success: bool, exam_id: Optional[UUID], error: Optional[str])
        """

    async def _validate_file(self, file_path: str) -> None:
        """ファイル存在・読み取り可能性を確認"""

    async def _parse_mfer_file(self, file_path: str) -> ParsedData:
        """MFERファイルを解析"""

    async def _register_patient(self, patient_data: PatientAttributes) -> Patient:
        """患者データを登録（既存チェック付き）"""

    async def _register_examination(
        self, exam_data: ExamMetadata, patient_id: UUID, file_path: str
    ) -> Examination:
        """検査データを登録（重複チェック付き）"""

    async def _move_file(self, file_path: str, exam_id: UUID, success: bool) -> str:
        """ファイルを移動（成功時: 処理済み、失敗時: エラー）"""
```

**依存関係**:
- `MFERParser`（Infrastructure層）
- `PatientRepository`（Domain層インターフェース）
- `ExaminationRepository`（Domain層インターフェース）
- `FileMover`（Infrastructure層）
- `DatabaseConnection`（Infrastructure層）

### 2. MFERParser（Infrastructure層）

**責務**: MFERファイルの解析、患者属性の抽出

**主要メソッド**:

```python
class MFERParser:
    def parse_patient_attributes(self, file_path: str) -> ParsedData:
        """MFERファイルから患者属性を抽出

        Returns:
            ParsedData(
                patient: PatientAttributes(
                    external_id: str,
                    name: str,
                    birth_date: date,
                    gender: str
                ),
                examination: ExamMetadata(
                    exam_date: datetime,
                    exam_type: str
                )
            )
        """

    def _parse_mfer_binary(self, file_data: bytes) -> MFERStructure:
        """MFERバイナリデータをパース"""

    def _extract_patient_info(self, mfer: MFERStructure) -> PatientAttributes:
        """患者情報を抽出"""

    def _extract_exam_metadata(self, mfer: MFERStructure) -> ExamMetadata:
        """検査メタデータを抽出"""

    def _skip_waveform_data(self, mfer: MFERStructure) -> None:
        """心電図波形データをスキップ（メモリ効率化）"""
```

**実装ノート**: MFERパーサーライブラリを使用。波形データは読み込まずスキップすることでメモリ使用量を削減。

### 3. PatientRepository / ExaminationRepository（Domain層インターフェース + Infrastructure層実装）

**責務**: 患者・検査データの永続化

**Domain層インターフェース**:

```python
class PatientRepository(Protocol):
    async def find_by_external_id(self, external_id: str) -> Optional[Patient]:
        """外部IDで患者を検索"""

    async def create(self, patient: Patient) -> Patient:
        """患者を作成"""

class ExaminationRepository(Protocol):
    async def find_duplicate(
        self, patient_id: UUID, exam_date: datetime
    ) -> Optional[Examination]:
        """重複検査を検索"""

    async def create(self, examination: Examination) -> Examination:
        """検査を作成"""

    async def update_file_path(self, exam_id: UUID, file_path: str) -> None:
        """ファイルパスを更新"""
```

**Infrastructure層実装**: SQLAlchemy ORMを使用

### 4. FileMover（Infrastructure層）

**責務**: ファイルの移動処理

**主要メソッド**:

```python
class FileMover:
    async def move_to_processed(self, file_path: str) -> str:
        """処理済みフォルダへ移動"""

    async def move_to_error(self, file_path: str) -> str:
        """エラーフォルダへ移動"""

    def _ensure_directory_exists(self, directory: str) -> None:
        """ディレクトリが存在しない場合は作成"""
```

### 5. ImportRouter（Presentation層）

**責務**: HTTP APIエンドポイントの提供

**主要メソッド**:

```python
@router.post("/api/import")
async def import_file(
    request: ImportRequest,
    service: ImportService = Depends(get_import_service)
) -> ImportResponse:
    """MFERファイルをインポート

    Request:
        {file_path: str}

    Response:
        {exam_id: UUID, status: "success"} (HTTP 200)
        {error: str} (HTTP 400/409/500)
    """
```

### 6. CLI Entry Point（Presentation層）

**責務**: コマンドラインインターフェース

```python
# app/cli/import.py
@click.command()
@click.argument("file_path", type=click.Path(exists=True))
def import_file(file_path: str) -> None:
    """MFERファイルをインポート（CLI）"""
    # ImportServiceを呼び出し
    # 終了コード0/1を返す
```

## データモデル

### PatientAttributes（Domain層 - Value Object）

```python
@dataclass
class PatientAttributes:
    """患者属性（MFERから抽出）"""
    external_id: str  # MFER内の患者ID
    name: str
    birth_date: date
    gender: str  # "男性" / "女性"
```

### ExamMetadata（Domain層 - Value Object）

```python
@dataclass
class ExamMetadata:
    """検査メタデータ（MFERから抽出）"""
    exam_date: datetime
    exam_type: str
```

### ParsedData（Application層）

```python
@dataclass
class ParsedData:
    """解析結果"""
    patient: PatientAttributes
    examination: ExamMetadata
```

### ImportResult（Application層）

```python
@dataclass
class ImportResult:
    """インポート結果"""
    success: bool
    exam_id: Optional[UUID] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None  # FILE, PARSE, VALIDATION, DB, IO
```

### Patient Entity（Domain層）

```python
class Patient(BaseEntity):
    """患者エンティティ"""
    id: UUID  # システム内部ID
    external_id: str  # MFER内の患者ID
    name: str
    birth_date: date
    gender: str
    created_at: datetime
```

### Examination Entity（Domain層）

```python
class Examination(BaseEntity):
    """検査エンティティ"""
    id: UUID
    patient_id: UUID  # Patientへの参照
    exam_date: datetime
    exam_type: str
    mfer_file_path: str
    inference_status: str  # 未実行/実行中/完了/エラー
    created_at: datetime
```

## エラーハンドリング

### エラー種別

| エラー種別 | HTTPステータス | 処理 | ログレベル |
|-----------|--------------|------|----------|
| ファイルエラー | 400 Bad Request | エラーフォルダへ移動 | ERROR |
| パースエラー | 400 Bad Request | エラーフォルダへ移動 | ERROR |
| バリデーションエラー | 400 Bad Request | エラーフォルダへ移動 | ERROR |
| 検査重複 | 409 Conflict | スキップ、ロールバック | WARNING |
| DBエラー | 500 Internal Server Error | ロールバック、エラーフォルダへ移動 | ERROR |
| IOエラー（ファイル移動失敗） | 200 OK | 警告ログ、DBは維持 | WARNING |

### エラーレスポンス形式

```json
{
  "error": "エラーメッセージ",
  "error_type": "PARSE_ERROR",
  "file_path": "/path/to/file.mwf"
}
```

## テスト戦略

### 単体テスト（Unit Tests）

**対象**: 各コンポーネントの個別テスト

| コンポーネント | テスト内容 |
|--------------|----------|
| `MFERParser` | MFERファイル解析、属性抽出、波形データスキップ |
| `ImportService` | 処理オーケストレーション、トランザクション管理 |
| `PatientRepository` | 患者検索、作成、既存チェック |
| `ExaminationRepository` | 検査検索、作成、重複チェック |
| `FileMover` | ファイル移動、ディレクトリ作成 |

**テストツール**: pytest, pytest-asyncio, pytest-mock

### 統合テスト（Integration Tests）

**対象**: コンポーネント間の連携テスト

- MFERParser → ImportService → Repository → Database の連携
- トランザクション管理のテスト（ロールバック確認）
- 実際のMFERファイルを使用したエンドツーエンドテスト
- 重複チェックの動作確認

**テストツール**: pytest, testcontainers（PostgreSQL）

### E2Eテスト（End-to-End Tests）

**対象**: HTTP API経由での全フロー確認

- `folder-watcher` からのHTTP POSTリクエストのシミュレーション
- 実際のデータベースを使用したインポート処理確認
- エラーケース（ファイル不存在、パースエラー等）の確認

### カバレッジ目標

- **Backend**: 80% 以上

## デプロイメント/インストールノート

### 開発環境（Docker Compose）

```yaml
# docker-compose.yml
services:
  file-importer:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/ecg_db
      - MFER_PROCESSED_FOLDER=/data/processed
      - MFER_ERROR_FOLDER=/data/error
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 本番環境（ローカルインストール）

**依存パッケージ**:
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
# MFERパーサーライブラリ（実装時に選択）
```

**起動コマンド（HTTP API）**:
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/ecg_db
export MFER_PROCESSED_FOLDER=/var/ecg/processed
export MFER_ERROR_FOLDER=/var/ecg/error
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**CLI使用例**:
```bash
python -m app.cli.import /path/to/file.mwf
```

**systemdサービス例**:
```ini
[Unit]
Description=File Importer Service
After=network.target postgresql.service

[Service]
Type=simple
User=ecg-user
WorkingDirectory=/opt/ecg-mi-inference/backend
Environment="DATABASE_URL=postgresql://user:pass@localhost:5432/ecg_db"
Environment="MFER_PROCESSED_FOLDER=/var/ecg/processed"
Environment="MFER_ERROR_FOLDER=/var/ecg/error"
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 設定要件

- データベース接続権限
- MFERファイルへの読み取り権限
- 処理済みフォルダ・エラーフォルダへの書き込み権限
- ポート8000の開放（HTTP API使用時）

---

**ステータス:** レビュー待ち
**作成日:** 2025-12-07
**最終更新:** 2025-12-07



