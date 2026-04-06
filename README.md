# ECG MI Inference

心電図（ECG）を用いた心筋梗塞（MI：Myocardial Infarction）診断支援システム

## 概要

本システムは、12誘導心電図データから心筋梗塞の検出・推論を行うWebアプリケーションです。

- **フロントエンド**: React 18 + TypeScript + Vite
- **バックエンド**: FastAPI (Python 3.13)
- **データベース**: SQLite (開発環境)

## クイックスタート

### 前提条件

- Docker Desktop (20.10+)
- Docker Compose (1.29+)
- Make (オプション、推奨)

### 起動方法

```bash
# 1. レポジトリをクローン
git clone https://github.com/Universal-Micro-Networks/ecg-mi-inference.git
cd ecg-mi-inference

# 2. Docker環境のセットアップと起動
make setup

# または Make を使わない場合
docker-compose build
docker-compose up -d
```

アプリケーションへのアクセス:
- **フロントエンド**: http://localhost:5173
- **バックエンドAPI**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

### よく使うコマンド

```bash
# 開発環境の起動（ログを表示しながら）
make dev

# サービスの停止
make down

# ログの確認
make logs

# データベースのリセット
make db-reset

# 完全なリセット（全削除→再ビルド→起動）
make reset

# ヘルプ（全コマンド一覧）
make help
```

## 機能

### 診察一覧 (Diagnosis List)

- 日付でフィルター可能な検査一覧の表示
- 患者ID・患者名での絞り込み（クライアント側）
- カラムごとのソート（exam_date, patient_id, patient_name, age）
- 検査の選択と推論実行

### 診察詳細 (Diagnosis Viewer)

- 検査詳細情報の表示
- ECG画像の表示（CSVから自動生成、キャッシュ対応）
- リアルタイム推論実行とポーリング（5秒間隔）
- 推論結果の表示（MI タイプ、重症度、信頼度スコア）

## プロジェクト構造

```
ecg-mi-inference/
├── frontend/           # Reactフロントエンド
│   ├── src/
│   │   ├── features/
│   │   │   ├── diagnosis-list/    # 一覧画面
│   │   │   └── diagnosis-viewer/  # 詳細画面
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── backend/            # FastAPIバックエンド
│   ├── app/
│   │   ├── api/
│   │   │   ├── examinations.py   # 検査API
│   │   │   └── inferences.py     # 推論API
│   │   ├── models.py             # SQLAlchemy モデル
│   │   ├── database.py           # DB接続・初期化
│   │   ├── ecg_service.py        # ECG画像生成
│   │   ├── inference_service.py  # 推論処理
│   │   └── main.py               # FastAPIアプリ
│   ├── data/                      # SQLiteデータベース
│   └── pyproject.toml             # uv 依存関係
├── docker-compose.yml  # Docker Compose設定
├── Dockerfile.frontend # フロントエンド Dockerfile
├── Dockerfile.backend  # バックエンド Dockerfile
├── Makefile            # 便利コマンド集
├── DOCKER.md           # Docker詳細ドキュメント
└── README.md           # このファイル
```

## 開発

### ローカル開発（Docker なし）

詳細なローカル開発環境のセットアップ手順は、各ディレクトリのREADMEを参照してください：
- **バックエンド**: [backend/README.md](backend/README.md) - uv を使ったセットアップ、依存関係管理、トラブルシューティング
- **フロントエンド**: [frontend/README.md](frontend/README.md) - npm を使ったセットアップ、利用可能なコマンド、トラブルシューティング

#### クイックスタート

**バックエンド（Python 3.13 + uv）**

```bash
cd backend
uv sync                                    # 依存関係のインストール
uv run uvicorn app.main:app --reload      # 開発サーバー起動（http://localhost:8000）
```

**フロントエンド（Node.js 20 + npm）**

```bash
cd frontend
npm install                    # 依存関係のインストール
npm run dev                    # 開発サーバー起動（http://localhost:5173）
```

### データベース

SQLiteデータベースは初回起動時に自動的に作成され、サンプルデータが投入されます。

- **場所**: `backend/data/ecg_mi.db`
- **スキーマ**:
  - `patients` - 患者情報
  - `examinations` - 検査記録
  - `inferences` - 推論結果

データベースのリセット:
```bash
make db-reset
```

### API エンドポイント

#### 検査 (Examinations)

- `GET /api/examinations` - 検査一覧取得（`exam_date` 必須。任意: `patient_id` / `patient_name`（部分一致）、`limit` / `offset`。応答 `{ items, total }`）
- `GET /api/examinations/{id}` - 検査詳細取得
- `GET /api/examinations/{id}/ecg-image` - ECG画像取得 (PNG)

#### 推論 (Inferences)

- `POST /api/inferences` - 推論実行開始
- `GET /api/inferences/{id}` - 推論ステータス・結果取得

詳細は http://localhost:8000/docs を参照してください。

## テスト

```bash
# バックエンドテスト
make test-backend

# フロントエンドテスト
make test-frontend
```

## トラブルシューティング

### ポートが使用中

ポート 5173 または 8000 が既に使用されている場合:
```bash
# プロセスを確認
lsof -i :5173
lsof -i :8000

# docker-compose.yml でポートを変更
```

### サービスが起動しない

```bash
# ログを確認
make logs-backend
make logs-frontend

# コンテナの状態を確認
docker-compose ps

# 完全リセット
make reset
```

### データベースエラー

```bash
# データベースをリセット
make db-reset
```

## ドキュメント

- [DOCKER.md](DOCKER.md) - Docker環境の詳細ドキュメント
- [backend/README.md](backend/README.md) - バックエンド詳細
- [.kiro/specs/](. kiro/specs/) - 機能仕様書

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。
