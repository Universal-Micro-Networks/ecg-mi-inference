# Project Structure

## Organization Philosophy

**モノレポ構成** - フロントエンド・バックエンドを単一リポジトリで管理。
**ドメイン駆動設計（DDD）** を採用し、ビジネスドメインを中心に設計。

- **Frontend**: MVVMアーキテクチャ + 機能単位（feature-based）構成
- **Backend**: Layeredアーキテクチャ（Presentation → Application → Domain → Infrastructure）

## Directory Patterns

### Root Structure
```
ecg-mi-inference/
├── .github/
│   └── workflows/      # GitHub Actions CI/CD
│       └── ci.yml      # メインCIワークフロー
├── frontend/           # React アプリケーション
├── backend/            # FastAPI アプリケーション
├── docker/             # Docker関連ファイル
├── scripts/            # ビルド・デプロイスクリプト
├── docs/               # ドキュメント
├── .pre-commit-config.yaml  # Pre-commit設定（FE/BE統一）
├── docker-compose.yml  # 開発環境定義
└── .kiro/              # AI-DLC 仕様・ステアリング
```

### Frontend (`/frontend`) - MVVM アーキテクチャ
**Purpose**: React SPAアプリケーション（MVVM + Storybook）

```
frontend/
├── .storybook/         # Storybook設定
│   ├── main.ts         # Storybook設定
│   └── preview.ts      # グローバルデコレーター
├── src/
│   │
│   │  ─────────── Model Layer ───────────
│   ├── api/            # 【自動生成】Orval生成のAPIクライアント
│   │   ├── model/      # 型定義（Pydanticスキーマから生成）
│   │   └── endpoints/  # APIクライアント関数
│   ├── domain/         # ドメインモデル・型定義
│   │   ├── patient/    # 患者ドメイン
│   │   │   └── types.ts
│   │   ├── ecg/        # 心電図ドメイン
│   │   └── inference/  # 推論ドメイン
│   │
│   │  ─────────── ViewModel Layer ───────────
│   ├── viewmodels/     # 共通ViewModel（Custom Hooks）
│   │   └── useAuth.ts  # 認証ViewModel
│   │
│   │  ─────────── View Layer ───────────
│   ├── components/     # 共通UIコンポーネント（Presentational）
│   │   └── ui/         # 汎用UI部品
│   │       ├── Button/
│   │       │   ├── Button.tsx
│   │       │   ├── Button.stories.tsx   # Storybook
│   │       │   └── Button.test.tsx      # Vitest
│   │       └── Modal/
│   │
│   │  ─────────── Feature Modules ───────────
│   ├── features/       # 機能単位モジュール（MVVM構成）
│   │   ├── auth/
│   │   │   ├── components/      # View: 認証UI
│   │   │   ├── hooks/           # ViewModel: useLogin, useLogout
│   │   │   └── index.ts
│   │   ├── patients/
│   │   │   ├── components/
│   │   │   │   ├── PatientList.tsx
│   │   │   │   └── PatientList.stories.tsx
│   │   │   ├── hooks/           # ViewModel: usePatients, usePatientDetail
│   │   │   └── index.ts
│   │   ├── ecg/
│   │   └── inference/
│   │
│   │  ─────────── Infrastructure ───────────
│   ├── lib/            # ユーティリティ（認証ヘッダー等）
│   ├── mocks/          # MSW APIモックハンドラー（Storybook/Test用）
│   ├── test/           # テストユーティリティ
│   │   └── setup.ts
│   │
│   ├── App.tsx         # ルートコンポーネント
│   └── main.tsx        # エントリーポイント
│
├── public/             # 静的ファイル
├── orval.config.ts     # Orval設定
├── vitest.config.ts    # Vitest設定
├── index.html
└── package.json
```

**MVVM レイヤー対応:**
| Layer | ディレクトリ | 責務 |
|-------|-------------|------|
| **Model** | `api/`, `domain/` | API通信、ドメイン型定義 |
| **ViewModel** | `viewmodels/`, `features/*/hooks/` | 状態管理、ビジネスロジック |
| **View** | `components/`, `features/*/components/` | UI描画（Storybook対応） |

**ファイル配置規則（Frontend）:**
- コンポーネント: `*.tsx`
- Storybook: `*.stories.tsx`（同じディレクトリ）
- テスト: `*.test.tsx`（同じディレクトリ）
- ViewModel: `use*.ts`（hooks/ディレクトリ）

> **Note**: `src/api/` は Orval により自動生成されるため、手動編集禁止。

### Backend (`/backend`) - Layered アーキテクチャ（DDD準拠）
**Purpose**: FastAPI REST APIサーバー

```
backend/
├── app/
│   │
│   │  ─────────── Presentation Layer ───────────
│   ├── api/            # APIエンドポイント（Controllers）
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── patients.py
│   │       ├── ecg.py
│   │       └── inference.py
│   ├── schemas/        # リクエスト/レスポンススキーマ（DTO）
│   │   ├── patient.py
│   │   ├── ecg.py
│   │   └── inference.py
│   │
│   │  ─────────── Application Layer ───────────
│   ├── services/       # アプリケーションサービス（Use Cases）
│   │   ├── patient_service.py
│   │   ├── ecg_service.py
│   │   ├── inference_service.py
│   │   └── mfer_watcher_service.py
│   │
│   │  ─────────── Domain Layer ───────────
│   ├── domain/         # ドメインモデル（ビジネスコア）
│   │   ├── patient/
│   │   │   ├── entity.py       # Patient エンティティ
│   │   │   ├── value_objects.py # PatientId, Name 等
│   │   │   └── repository.py   # Repository インターフェース
│   │   ├── ecg/
│   │   │   ├── entity.py       # ECGRecord エンティティ
│   │   │   └── repository.py
│   │   ├── inference/
│   │   │   ├── entity.py       # InferenceResult エンティティ
│   │   │   ├── value_objects.py # RiskScore 等
│   │   │   └── domain_service.py # 推論ドメインサービス
│   │   └── shared/             # 共通ドメインオブジェクト
│   │       └── base_entity.py  # UUID PK ベースクラス
│   │
│   │  ─────────── Infrastructure Layer ───────────
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── connection.py   # DB接続
│   │   │   └── models/         # SQLAlchemy ORMモデル
│   │   │       ├── patient.py
│   │   │       ├── ecg.py
│   │   │       └── inference.py
│   │   ├── repositories/       # Repository 実装
│   │   │   ├── patient_repository.py
│   │   │   ├── ecg_repository.py
│   │   │   └── inference_repository.py
│   │   ├── external/           # 外部サービス連携
│   │   │   └── mfer_parser.py  # MFERファイル解析
│   │   └── ml/                 # 機械学習モデル
│   │       └── vit_model.py    # Vision Transformer
│   │
│   │  ─────────── Core ───────────
│   ├── core/           # 横断的関心事
│   │   ├── config.py   # 設定
│   │   ├── security.py # 認証・認可
│   │   └── exceptions.py # カスタム例外
│   │
│   └── main.py         # エントリーポイント
│
├── tests/              # テスト（レイヤー別）
│   ├── conftest.py     # 共通fixture
│   ├── unit/           # 単体テスト
│   │   ├── domain/     # ドメイン層テスト
│   │   └── services/   # アプリケーション層テスト
│   ├── integration/    # 統合テスト
│   │   └── api/        # APIエンドポイントテスト
│   └── e2e/            # E2Eテスト
├── alembic/            # マイグレーション
├── requirements.txt    # 本番依存
├── requirements-dev.txt  # 開発依存（pytest, pyrefly, ruff等）
└── pyproject.toml      # プロジェクト設定（ruff, pytest設定含む）
```

**Layered アーキテクチャ対応:**
| Layer | ディレクトリ | 責務 | 依存可能 |
|-------|-------------|------|---------|
| **Presentation** | `api/`, `schemas/` | HTTP処理、DTO | Application |
| **Application** | `services/` | ユースケース、トランザクション | Domain |
| **Domain** | `domain/` | エンティティ、ビジネスルール | なし（コア） |
| **Infrastructure** | `infrastructure/` | DB、外部サービス、ML | Domain |
| **Core** | `core/` | 横断的関心事（設定、例外） | なし |

**依存関係ルール（DDD）:**
- Domain層は他のどの層にも依存しない（純粋なビジネスロジック）
- Infrastructure層はDomain層のインターフェース（Repository）を実装
- 依存性注入（DI）でInfrastructure→Domainの依存を逆転

**テストファイル配置規則（Backend）:**
- `tests/unit/`: 単体テスト（モック使用、高速）
- `tests/integration/`: 統合テスト（DB使用）
- `tests/e2e/`: エンドツーエンドテスト
- ファイル名: `test_*.py`

### Docker (`/docker`)
**Purpose**: コンテナビルド定義

```
docker/
├── frontend/
│   └── Dockerfile
├── backend/
│   └── Dockerfile
└── db/
    └── init.sql        # 初期化スクリプト
```

## Naming Conventions

### Files
| Layer | Pattern | Example |
|-------|---------|---------|
| Frontend Components | PascalCase | `PatientList.tsx`, `EcgChart.tsx` |
| Frontend Hooks | camelCase + use prefix | `usePatients.ts`, `useInference.ts` |
| Frontend Utils | camelCase | `apiClient.ts`, `formatDate.ts` |
| Backend Modules | snake_case | `patient_service.py`, `ecg_parser.py` |
| Backend Tests | test_ prefix | `test_inference.py` |

### Functions / Variables
- **Frontend**: camelCase（`fetchPatients`, `inferenceResult`）
- **Backend**: snake_case（`fetch_patients`, `inference_result`）

### Components
- PascalCase for component names
- Props interface: `{ComponentName}Props`

```typescript
interface PatientListProps {
  patients: Patient[];
  onSelect: (id: string) => void;
}

export const PatientList: React.FC<PatientListProps> = ({ patients, onSelect }) => {
  // ...
};
```

## Import Organization

### Frontend
```typescript
// 1. External libraries
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Absolute imports (path alias)
import { Button } from '@/components/ui/Button';
import { usePatients } from '@/features/patients/hooks/usePatients';
import { Patient } from '@/types/patient';

// 3. Relative imports (same feature)
import { PatientCard } from './PatientCard';
```

**Path Aliases**:
- `@/`: `frontend/src/`

### Backend
```python
# 1. Standard library
from datetime import datetime
from pathlib import Path

# 2. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 3. Local application
from app.core.config import settings
from app.models.patient import Patient
from app.services.inference import InferenceService
```

## Code Organization Principles

1. **Feature Colocation**
   関連するコード（コンポーネント、フック、型）は同じfeatureディレクトリに配置

2. **Dependency Direction**
   `features/` → `components/ui/` → `lib/` の方向で依存（逆方向禁止）

3. **API Layer Isolation**
   フロントエンドのAPI呼び出しは `lib/apiClient.ts` 経由で統一

4. **Service Layer Pattern（Backend）**
   ビジネスロジックは `services/` に集約、APIエンドポイントは薄く保つ

5. **環境非依存**
   環境固有の設定は環境変数 or 設定ファイルで外部化

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_

