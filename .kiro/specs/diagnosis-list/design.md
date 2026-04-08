# 設計書: 診察一覧機能 (diagnosis-list)

## 目的
診察一覧の取得・表示・フィルタリング・ソート・選択を行い、**同一ルート上で右スライドパネル**により診察詳細を表示する。

## 画面/ルーティング
- 画面: 診察一覧（＋詳細スライドパネル）
- ルート: `/diagnoses`
- クエリ: `exam_date` (YYYY-MM-DD, 必須), `sort_by`, `sort_order`, `limit`, `offset`, **`detail`（任意・診察 UUID）**
  - 初回アクセス時に `exam_date` が未指定なら当日を自動設定する
  - `detail` があるとき `DiagnosisDetailPanel` を開き、`ExaminationDetailView` を表示する
- レガシー `/diagnoses/:id` → `DiagnosisLegacyRedirect` で `?detail=` へ寄せる（`diagnosis-viewer` 側エクスポート）

## API設計
- `GET /api/examinations`
  - Query: `exam_date` (必須), `sort_by` (default: `exam_date`), `sort_order` (default: `desc`), `patient_id` (任意, 部分一致), `patient_name` (任意, 部分一致), `limit` (default: 50), `offset` (default: 0)
  - Response: `{ items: 診察一覧, total: 総件数 }`
  - 認可: JWTをヘッダーに付与

## フロントエンド設計

### コンポーネント構成
- `DiagnosisListPage` — `detail` / `panelOpen` / `renderId` の同期、`setSearchParams`
- `DiagnosisDetailPanel` — オーバーレイ、`aside` スライド（幅約 2/3）、`transitionend` で URL 更新
- `FilterPanel`
- `DiagnosisTable` — 行クリックで `openDetail(id)`
- `SortHeader`
- `EmptyState`
- `ErrorState`

### ViewModel (Hooks)
- `useDiagnosisList`
  - `exam_date`, `sort_by`, `sort_order`, `patient_id`, `patient_name`, `limit`, `offset` を引数に一覧取得
  - TanStack Queryでキャッシュ/再取得
- `useDiagnosisFilters`
  - 患者ID/氏名の入力値と検索確定値を分離して保持
  - Enter/Return で確定して API クエリに反映
- `useExaminationsSse`
  - `GET /api/examinations/events` を `fetch + Authorization` で購読
  - `examinations_changed` 受信時に `["examinations"]` を invalidate
  - 切断時は一定間隔で再接続
- `useSortQueryParams`
  - URLクエリとソート状態を同期
### 状態管理
- サーバー状態: TanStack Query
- UI状態: React local state
- フィルター: 患者ID/氏名は Enter 確定時のみ API クエリへ反映

### リフレッシュ
- SSE (`/api/examinations/events`) による push 型更新
- 画面フォーカス時に再取得 (`refetchOnWindowFocus`)

## 表示仕様
- 初期ソート: 検査日時 降順
- 総件数とページ範囲を表示
- フィルター結果0件: メッセージ表示
- ローディング/エラー表示

## アクセシビリティ
- テーブル行のフォーカス移動
- `aria-sort` 付与
- ボタン/入力のラベル付与

## エラーハンドリング
- API失敗: エラーメッセージ
- 認可失敗: ログイン画面へリダイレクト

## テスト方針
- `FilterPanel` の Enter 確定動作（IME 変換中 Enter 除外）
- ソート切替とクエリ同期
- 0件表示とエラー表示
- 選択行ハイライト
- `detail` クエリとパネル開閉・Escape（モーダル優先）の挙動
- SSE 受信時の `examinations` クエリ再取得

## 非機能
- 取得から表示まで2秒以内
- 当日分のみをサーバー側で取得

---

**最終更新:** 2026-04-07（Enter確定検索・SSE購読の設計反映）
