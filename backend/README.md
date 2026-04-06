# ECG MI Inference Backend

FastAPI-based backend for ECG examination and MI (Myocardial Infarction) inference system.

## 前提条件

- Python 3.13 以上
- uv

### uv のインストール

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Homebrew
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## ローカル開発環境のセットアップ

uv は高速なPythonパッケージマネージャーで、依存関係の管理とインストールを効率的に行えます。

```bash
# 1. バックエンドディレクトリに移動
cd backend

# 2. 依存関係をインストール（仮想環境も自動作成）
uv sync

# 3. 開発サーバーを起動
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## アクセス

起動後、以下のURLでアクセスできます：

- **API**: `http://localhost:8000`
- **Swagger UI** (対話的APIドキュメント): `http://localhost:8000/docs`
- **ReDoc** (APIドキュメント): `http://localhost:8000/redoc`
- **ヘルスチェック**: `http://localhost:8000/health`

## 依存関係の管理

```bash
# 新しいパッケージを追加
uv add <package-name>

# 開発用パッケージを追加
uv add --dev <package-name>

# 依存関係を更新
uv sync --upgrade

# インストール済みパッケージの確認
uv pip list
```

## データベース

初回起動時に自動的にSQLiteデータベース (`data/ecg_mi.db`) が作成され、サンプルデータが投入されます。

### データベースのリセット

```bash
# データベースファイルを削除して再起動
rm -f data/ecg_mi.db
uv run uvicorn app.main:app --reload
```

## テスト

```bash
# テストを実行
uv run pytest

# カバレッジ付きでテスト
uv run pytest --cov=app --cov-report=html
```

## トラブルシューティング

### ポート8000が既に使用されている

```bash
# ポートを使用しているプロセスを確認
lsof -i :8000

# 別のポートで起動
uvicorn app.main:app --reload --port 8001
```

### モジュールが見つからないエラー

```bash
# 依存関係を再インストール
uv sync --reinstall
```

### データベースエラー

```bash
# データベースファイルを削除して再作成
rm -f data/ecg_mi.db
# サーバーを再起動すると自動的に再作成されます
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app setup, CORS, startup events
│   ├── models.py            # SQLAlchemy ORM models (Patient, Examination, Inference)
│   ├── database.py          # Database connection, session management, sample data init
│   ├── ecg_service.py       # ECG image generation from CSV (matplotlib)
│   ├── inference_service.py # Inference status management and simulation
│   ├── data.py              # Legacy sample data (deprecated)
│   └── api/
│       ├── __init__.py
│       ├── examinations.py  # examinations + ecg-image + export-wave-csv
│       └── inferences.py    # POST /api/inferences, GET /api/inferences/{id}
├── data/
│   ├── ecg_mi.db           # SQLite database (auto-created)
│   └── ecg_cache/          # Cached ECG PNG images
├── requirements.txt
└── README.md
```

## API Endpoints

### Examinations

- `GET /api/examinations` - List examinations with server-side filters and pagination
  - Query params: `exam_date` (required), `sort_by`, `sort_order`, `patient_id`, `patient_name`, `limit`, `offset`
  - Response: `{ "items": [...], "total": <number> }`

- `GET /api/examinations/{examination_id}` - Get examination detail（`mfer_file_path` / `csv_file_path` / `created_at` など）
- `POST /api/examinations/{examination_id}/export-wave-csv` - MFER を再読込し `mfer_tools.extract_mfer_data` + `save_wave_csv` で波形 CSV を `data/waves/{id}.csv` に出力し、`csv_file_path` を更新

- `GET /api/examinations/{examination_id}/ecg-image` - Get ECG image as PNG
  - Returns ETag headers for caching

### Inferences

- `POST /api/inferences` - Start new inference
  - Body: `{"examination_id": "..."}`
  - Returns inference ID and status "実行中"

- `GET /api/inferences/{inference_id}` - Get inference status/results
  - Polls inference status, returns results when complete

## File Importer (folder-watcher 連携)

`folder-watcher` は `app.file_importer.import_mfer_file(file_path)` を呼び出します。

- **入力**: `file_path` (絶対パス推奨、`.mwf/.MWF` を大文字小文字無視で受理)
- **戻り値**: `None`（成功時）
- **例外**: `FileImporterError` または下位例外（失敗時）

処理内容（概要）:
- `mfer_tools.extract_mfer_header()` で MFER ヘッダー抽出
- 同名 XML (`.XML/.xml`) から不足項目を補完
- `patients` / `examinations` / `inferences` へ登録
- 成功時: `MFER_PROCESSED_FOLDER`、失敗時: `MFER_ERROR_FOLDER` へ移動

### file-importer 関連環境変数

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `MFER_PROCESSED_FOLDER` | - | `./processed` | 正常処理ファイルの移動先 |
| `MFER_ERROR_FOLDER` | - | `./error` | エラーファイルの移動先 |
| `MFER_WATCH_FOLDER` | folder-watcher側で必須 | - | 監視対象フォルダ |

## Database

SQLite database with three main tables:

1. **patients** - Patient demographic information
2. **examinations** - ECG examination records with CSV file paths
3. **inferences** - Inference execution results and status

Database is auto-initialized on startup with sample data.

## ECG Image Generation

ECG images are generated on-demand from CSV files using matplotlib:
- Reads signal data from CSV
- Generates 12-lead ECG visualization
- Caches PNG on disk with ETag support
- Falls back to synthetic ECG for demo if CSV not found

## Inference Simulation

Inference execution is simulated with time-based completion:
- POST creates inference with `status = "実行中"`
- Client polls GET every 5 seconds
- After ~20-30 seconds of polling, status changes to "完了" with ML results
- Results include MI type, severity, confidence score, probability

## CORS Configuration

Configured to allow requests from:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (React dev server)
- `*` (wildcard for development)

Restrict in production by modifying `app/main.py`.

## Development

### Logging & Debugging

Set `echo=True` in `database.py` to see SQL queries:
```python
engine = create_engine(DATABASE_URL, echo=True)
```

### Clear Cache

```python
from app.ecg_service import clear_ecg_cache
clear_ecg_cache()
```

### Reset Database

Delete `backend/data/ecg_mi.db` and restart the server.
