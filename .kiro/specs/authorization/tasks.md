# タスク一覧: 認可機能 (authorization)

## 目的

`authorization/design.md` に基づき、Frontend/Backend の認可（パスワードのみ・単一ユーザー）を実装可能な粒度へタスク分解する。

## 前提・スコープ

- 初期実装は **`localStorage` にトークン保存**（`Authorization: Bearer`）とする
- ログアウトは access token の `jti` を **ブラックリスト登録**して失効扱いにする
- 初期パスワードは `INITIAL_ADMIN_PASSWORD` がある場合に DB へ保存し、無い場合は起動エラーとする

## 実装順序（推奨）

- Backend の **トークン/検証**（TokenService + Middleware）を先に作り、API の 401/422 形を固定する
- 次に `login/refresh/logout` API を固め、最後に Frontend の `useAuth` と ProtectedRoute を接続する

## タスク

### 1. Backend: 認可 API / ドメイン / インフラ

- [x] **1.1 スキーマ追加**
  - **ファイル**: `backend/app/schemas/auth.py`
  - **内容**:
    - `LoginRequest`, `TokenResponse`, `RefreshRequest`, `AccessTokenResponse`, `ChangePasswordRequest`, `MessageResponse`
    - エラーの `detail` 文字列方針（設計の表に沿う）

- [x] **1.2 ドメイン例外の追加**
  - **ファイル**: `backend/app/domain/auth/exceptions.py`
  - **内容**:
    - `AuthenticationError`, `InvalidTokenError`, `TokenExpiredError`, `PasswordPolicyError`

- [x] **1.3 パスワードポリシー検証**
  - **ファイル**: `backend/app/domain/auth/password_validator.py`
  - **内容**:
    - 最低長、文字種 3/4 を検証
    - 強度計算（`weak|medium|strong`）を仕様化したロジックで返す

- [x] **1.4 TokenService 実装**
  - **ファイル**: `backend/app/infrastructure/auth/token_service.py`
  - **内容**:
    - HS256 署名、`JWT_SECRET_KEY` 取得
    - access token: `type=access` + `jti` + exp/iat
    - refresh token: `type=refresh` + exp/iat（初期は jti なし）
    - `verify_access_token` / `verify_refresh_token` の例外マッピング

- [x] **1.5 PasswordRepository 実装**
  - **ファイル**: `backend/app/infrastructure/repositories/password_repository.py`
  - **内容**:
    - `system_config(key='system_password')` の取得/更新
    - passlib(bcrypt) で verify / hash（work factor=12）

- [x] **1.6 TokenBlacklist 永続化（DB + Repository）**
  - **内容**:
    - `token_blacklist` テーブル追加（`token_jti`, `expires_at`）
    - access token 検証時に `jti` がブラックリストに存在したら 401 扱い
  - **実装方針**:
    - 既存の DB 管理方式に合わせ、モデル/アクセス層を追加（必要なら migration も）

- [x] **1.7 AuthService 実装**
  - **ファイル**: `backend/app/services/auth_service.py`
  - **内容**:
    - `login(password)`:
      - パスワード検証 → token pair 発行
      - 失敗は `AuthenticationError`
    - `refresh_token(refresh_token)`:
      - refresh 検証 → 新 access token 発行
    - `logout(access_token)`:
      - access 検証して `jti` をブラックリスト登録（`expires_at` は token の exp）
    - `change_password(current, new)`:
      - current 検証 → new を `PasswordValidator` で検証 → 更新

- [x] **1.8 AuthRouter 実装**
  - **ファイル**: `backend/app/api/v1/auth.py`
  - **内容**:
    - `POST /api/v1/auth/login`
    - `POST /api/v1/auth/refresh`
    - `POST /api/v1/auth/logout`
    - `PUT /api/v1/auth/password`
  - **エラーハンドリング**:
    - 401/422 のレスポンス整形（設計の表に沿う）

- [x] **1.9 認可ミドルウェア/依存関係**
  - **ファイル**: `backend/app/core/middleware/auth_middleware.py`（または既存の依存関係注入パターンに合わせる）
  - **内容**:
    - `Authorization: Bearer <token>` を検証
    - 除外パス（login/refresh/docs/openapi 等）を明示
    - 401 の detail 文言を統一

- [x] **1.10 初期パスワード設定**
  - **内容**:
    - 起動時に `system_password` 未設定なら
      - `INITIAL_ADMIN_PASSWORD` があれば hash 化して DB 保存
      - 無ければ起動エラー（設定要求）
  - **実装箇所**:
    - `backend/app/main.py` もしくは設定初期化箇所（既存の初期化フローに合わせる）

### 2. Frontend: ログイン UI / ルート保護 / トークン運用

- [x] **2.1 AuthContext 実装**
  - **ファイル**: `frontend/src/features/auth/AuthContext.tsx`
  - **内容**:
    - `isAuthenticated`, `accessToken`, `setAuth`, `clearAuth`
    - 初期化時に localStorage から復元

- [x] **2.2 useAuth Hook 実装**
  - **ファイル**: `frontend/src/features/auth/hooks/useAuth.ts`
  - **内容**:
    - `login(password)` → `/auth/login` 呼び出し → localStorage 保存 → context 更新
    - `refreshToken()` → `/auth/refresh` 呼び出し → access 更新
    - `logout()` → `/auth/logout` 呼び出し（失敗しても local state はクリア）→ localStorage 削除
    - 自動リフレッシュ方針:
      - access 期限が残り1時間以内なら次リクエスト前に refresh
      - 期限切れ時は refresh を試み、refresh も失効ならログイン画面へ

- [x] **2.3 LoginPage 実装**
  - **ファイル**: `frontend/src/features/auth/components/LoginPage.tsx`
  - **内容**:
    - パスワード入力、表示切替、エラー表示、成功時リダイレクト
    - 誤パスワード時に入力をクリア

- [x] **2.4 PasswordStrengthIndicator 実装（UI）**
  - **ファイル**: `frontend/src/features/auth/components/PasswordStrengthIndicator.tsx`
  - **内容**:
    - strength 表示（`weak|medium|strong`）
    - どのロジックで strength を出すかを `useAuth` / `LoginPage` と整合させる

- [x] **2.5 ProtectedRoute 実装**
  - **ファイル**: `frontend/src/features/auth/components/ProtectedRoute.tsx`
  - **内容**:
    - 未認可ならログインへリダイレクト
    - 認可状態の初期化中はローディング表示（ちらつき抑制）

- [x] **2.6 API クライアントへの Authorization 付与**
  - **内容**:
    - 既存の API 呼び出し統一箇所（`lib/` や Orval の fetch ラッパ）に Bearer 付与
    - 401 を捕捉して refresh → 再試行の動線（必要なら 1 回まで）

- [x] **2.7 ルーティング組み込み**
  - **内容**:
    - `/login` 追加
    - 既存ページを `ProtectedRoute` で保護（設計通り “login 以外は保護”）

### 3. DB: テーブル追加/更新

- [x] **3.1 system_config の整備**
  - **内容**:
    - `system_config(key='system_password')` の保存先を確定（既存 DB との整合）
    - UUID 生成は `gen_random_uuid()` に統一（steering 準拠）

- [x] **3.2 token_blacklist の追加**
  - **内容**:
    - `token_jti` の一意制約
    - `expires_at` で期限切れを管理（必要ならクリーンアップ戦略を追加）

### 4. テスト

- [x] **4.1 Backend Unit**
  - **PasswordValidator**: 境界値（長さ、文字種）と strength
  - **TokenService**: access/refresh の生成と検証、期限切れ例外

- [x] **4.2 Backend Integration**
  - `POST /auth/login`: 成功/失敗（401 detail）
  - `POST /auth/refresh`: 成功/失敗
  - **保護 API**: 未認可 401、認可 OK
  - `POST /auth/logout`: ログアウト後に同 access token が拒否される（ブラックリスト）

- [x] **4.3 Frontend**
  - `useAuth`: login/logout/refresh の状態遷移、localStorage の読み書き
  - `ProtectedRoute`: 未認可リダイレクト、初期化中の表示

## 完了条件

- FE/BE のログイン〜保護ページ閲覧〜ログアウトが一通り動く
- 401/422 の文言と挙動が `authorization/design.md` と一致する
- 最低限の単体・統合テストが通る

## レビュー観点（Tasks 承認チェックリスト）

- **抜け漏れ**: FE/BE/DB/テストが揃っている（特に logout のブラックリスト検証）
- **依存順**: DB 追加（`system_config` / `token_blacklist`）が実装タスクに含まれている
- **非機能**: 最低限のログ（ログイン成功/失敗、ログアウト）がタスクに含まれている

