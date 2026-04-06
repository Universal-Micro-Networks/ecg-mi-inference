# 設計書: 診察一覧機能 (diagnosis-list)

## 目的
診察一覧の取得・表示・フィルタリング・ソート・選択を行い、診察詳細/推論へ遷移できるUIを提供する。

## 画面/ルーティング
- 画面: 診察一覧
- ルート: `/diagnoses`
- クエリ: `exam_date` (YYYY-MM-DD, 必須), `sort_by`, `sort_order`, `limit`, `offset`
  - 初回アクセス時に `exam_date` が未指定なら当日を自動設定する

## API設計
- `GET /api/examinations`
  - Query: `exam_date` (必須), `sort_by` (default: `exam_date`), `sort_order` (default: `desc`), `patient_id` (任意, 部分一致), `patient_name` (任意, 部分一致), `limit` (default: 50), `offset` (default: 0)
  - Response: `{ items: 診察一覧, total: 総件数 }`
  - 認可: JWTをヘッダーに付与

## フロントエンド設計

### コンポーネント構成
- `DiagnosisListPage`
- `FilterPanel`
- `DiagnosisTable`
- `SortHeader`
- `RefreshButton`
- `EmptyState`
- `ErrorState`

### ViewModel (Hooks)
- `useDiagnosisList`
  - `exam_date`, `sort_by`, `sort_order`, `patient_id`, `patient_name`, `limit`, `offset` を引数に一覧取得
  - TanStack Queryでキャッシュ/再取得
- `useDiagnosisFilters`
  - 患者ID/氏名フィルター (サーバー検索条件として保持)
  - 500msデバウンス
- `useSortQueryParams`
  - URLクエリとソート状態を同期
- `useRowSelection`
  - 選択行の状態管理

### 状態管理
- サーバー状態: TanStack Query
- UI状態: React local state
- フィルター: 患者ID/氏名はデバウンス後にAPIクエリへ反映

### リフレッシュ
- 手動リフレッシュボタン
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
- `FilterPanel` の入力/クリア動作
- ソート切替とクエリ同期
- 0件表示とエラー表示
- 選択行ハイライト

## 非機能
- 取得から表示まで2秒以内
- 当日分のみをサーバー側で取得

---

**最終更新:** 2026-04-07
