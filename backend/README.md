# ECG MI Inference Backend

FastAPI-based backend for ECG examination and MI (Myocardial Infarction) inference system.

## 前提条件

- Python 3.12 以上（`pyproject.toml` の `requires-python` に準拠）
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

# ECG→BNP 推論はコア機能のため `uv sync` で `inference-ecg-bnp` と PyTorch 群が入る。
# Git に届かない環境では `make vendor-inference-bnp` で vendor の src を置くフォールバック可。
# 設定の渡し方は次のいずれか（優先順は上）。
#   A) アプリ起動時などに Python から `from app.bnp_inference import set_bnp_inference_config`
#      で辞書を渡す（YAML ファイルは不要。重みパス等は呼び出し側で組み立てる）。
#   B) 環境変数 `ECG_BNP_INFERENCE_CONFIG_JSON` に JSON オブジェクト文字列。
#   C) 環境変数 `ECG_BNP_INFERENCE_CONFIG` に YAML パス（`backend/` からの相対可）。
#      リポジトリ同梱の例: `config/bnp_infer.yaml`（重みは `data/models/*.pth`、gitignore 済み）。
# いずれも `checkpoint_path` は必須。相対パスは `set_bnp_inference_config(..., path_base=...)` の
# `path_base`、または YAML ファイルのあるディレクトリ基準（上流の解決）／`backend/` 基準（JSON）で解決。

# 3. 開発サーバーを起動
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker を使わないスタンドアローン実行

Docker なしでバックエンド（必要ならフロントも別プロセス）だけを動かす手順です。パス解決（`ECG_BNP_INFERENCE_CONFIG` の相対パス、`data/` など）は **`backend/` をカレントディレクトリにした状態**で `uv run` することを前提にしています。

### 最短の流れ（コピペ用）

リポジトリをクローン済みで、ルートに `.env`（少なくとも `JWT_SECRET_KEY`、BNP を使うなら `ECG_BNP_INFERENCE_CONFIG` 等）がある想定です。

```bash
cd backend
set -a && source ../.env && set +a   # bash/zsh。Windows は手動で同等の環境変数を設定
uv sync                              # 失敗したらリポジトリルートで make vendor-* 後に再実行
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000 ・ドキュメント: http://localhost:8000/docs
- バックエンドの単体テスト: 同じ `backend/` で `uv run pytest`

以下は手順の補足です。

### 1. 作業ディレクトリ

Python / uv は冒頭の「前提条件」を満たしてください。以降のコマンドは **`backend/` をカレントディレクトリにした状態**で実行します（相対パス・BNP 設定の解決が安定します）。

### 2. 環境変数

- リポジトリルートに置いた `.env` をそのまま使う場合、`backend/` に移動したうえでシェルから読み込みます。

```bash
cd backend
set -a && source ../.env && set +a   # bash/zsh の例（.env は KEY=value 形式）
```

- 最低限 **`JWT_SECRET_KEY`** が必要です（未設定だと起動時に失敗します）。
- BNP 推論を有効にする場合は **`ECG_BNP_INFERENCE_CONFIG`**（例: `config/bnp_infer.yaml`）や `set_bnp_inference_config`／`ECG_BNP_INFERENCE_CONFIG_JSON` のいずれか。詳細は上記コメントブロック参照。

[direnv](https://direnv.net/) でルートの `.env` を自動読込する運用でも構いません。

### 3. 依存のインストール

```bash
cd backend
uv sync
```

`pyproject.toml` の **Git 依存**（`mfer-tools` / `inference-ecg-bnp`）が非公開で `uv sync` が失敗する場合は、リポジトリルートで `make vendor-mfer-tools` と `make vendor-inference-bnp` を実行したうえで再度 `uv sync` してください（`app/bnp_inference` が vendor の `src` をフォールバックで参照します）。

### 4. サーバの起動

開発用（コード変更で自動リロード）:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

本番に近い単一プロセス（リロードなし）:

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- **SQLite** を使うため、**複数ワーカー**（`--workers 2` など）は推奨しません。原則ワーカー 1 本でください。
- プロセスマネージャ（systemd、supervisor 等）に載せる場合も、上記と同様に **`WorkingDirectory=.../backend`** と `ExecStart=.../uv run uvicorn ...` を指定するとパスが安定します。

### 5. データ・設定・重み

| 種別 | 場所（`backend/` からの相対） |
|------|--------------------------------|
| SQLite | `data/ecg_mi.db`（初回アクセスで作成） |
| BNP 設定例 | `config/bnp_infer.yaml` |
| 学習済み重み（例） | `data/models/*.pth`（`.gitignore` 済み） |

### 6. フロントエンド

フロントは Docker なしでは別ターミナルで起動します（例: リポジトリルートで `cd frontend && npm ci && npm run dev`）。API の向き先は Vite の環境変数（例: `VITE_API_URL`）やプロキシ設定で、上記バックエンドのホスト・ポートに合わせてください。

## Raspberry Pi（ARM64）で BNP 推論を動かすとき

- **OS**: 64 ビット（例: Raspberry Pi OS 64-bit）を推奨します。32 ビット ARM では PyTorch のホイールが揃わないことが多いです。
- **デバイス**: BNP 用 YAML（例: `config/bnp_infer.yaml`）の `device` は常に `"cpu"` にしてください（CUDA は使いません）。
- **PyTorch の入れ方**: 開発用 PC（macOS / x86 Linux など）で作った `uv.lock` を Pi に持ち込んだとき、**ARM 向けホイールと一致しない**ことがあります。Pi 上で `uv sync` を実行し、解決に失敗したら [PyTorch の Get Started](https://pytorch.org/get-started/locally/) で Linux + CPU + Pip の組み合わせを選び、表示される `--index-url`（例: `https://download.pytorch.org/whl/cpu`）に従って `torch` / `torchvision` / `torchaudio` を入れ直す方法が確実です。
- **メモリと初回ロード**: Swin 系のモデルは重いです。RAM が少ないボードでは OOM や初回モデルロードの長時間化があり得るため、**実機で一度だけ**推論時間とメモリ使用量を計測してください。
- **Docker**: 現状の `Dockerfile.backend` は x86_64 での利用を主に想定しています。ARM でコンテナ運用する場合は、**Pi 上で `linux/arm64` 向けにビルド**するか、イメージ内の `pip install torch` を ARM 用 CPU ホイールに合わせて見直してください。

## アクセス

`uvicorn` を **この README の手順どおり**（ホスト上、`--port 8000`）で動かした場合の URL です。Docker Compose 経由ではホスト側は **8200** にマッピングされているため、`http://localhost:8200` になります（ルートの `README.md` 参照）。

- **API**: `http://localhost:8000`
- **Swagger UI** (対話的APIドキュメント): `http://localhost:8000/docs`
- **ReDoc** (APIドキュメント): `http://localhost:8000/redoc`
- **ヘルスチェック**: `http://localhost:8000/health`

## 依存関係の管理

```bash
# 新しいパッケージを追加
uv add <package-name>

# 開発用パッケージを追加
uv add --group dev <package-name>

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

- `GET /api/examinations/{examination_id}/ecg-image` - 心電図 PNG（matplotlib 12 誘導）
  - 取得前に `data/waves/{id}.csv` を優先し、無ければ MFER から `extract_mfer_data` + `save_wave_csv` で自動出力してから、その CSV を入力に画像生成する（`csv_file_path` を同期する場合あり）
  - `If-None-Match` が DB の ETag と一致すれば 304（本文・再エクスポートなし）

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
| `MFER_WATCH_FOLDER` | folder-watcher側で必須 | - | 監視対象フォルダ（相対・絶対、`~` 可） |
| `MFER_WATCH_USE_POLLING` | - | `false` | ネットワーク共有向けに PollingObserver を使う |
| `MFER_WATCH_POLLING_INTERVAL_SEC` | - | `1` | ポーリング間隔（秒） |

## Database

SQLite database with three main tables:

1. **patients** - Patient demographic information
2. **examinations** - ECG examination records with CSV file paths
3. **inferences** - Inference execution results and status

Database is auto-initialized on startup with sample data.

## ECG Image Generation

ECG images are generated on-demand from CSV files using matplotlib:

- Reads `time` plus standard lead columns (`I`, `II`, `III`, `aVR`, `aVL`, `aVF`, `V1`–`V6`) when present (same shape as `mfer_tools.save_wave_csv` output).
- Renders a **single PNG** with a **6×2 grid** of subplots. Missing leads show a placeholder in their cell.
- Legacy CSV with only one numeric column is plotted as **lead II**; other cells stay empty.
- Title includes sampling rate (Hz); rate is inferred from the `time` column when available, otherwise 250 Hz is assumed.
- Caches PNG under `data/ecg_cache/` with a versioned cache key; ETag support unchanged.
- If the CSV is missing, unreadable, or has no usable lead data, `generate_ecg_image` raises **`EcgWaveformLoadError`** (no synthetic / demo waveform). The `ecg-image` API responds with **422** and a Japanese error detail.

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
