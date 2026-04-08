# タスク一覧: 診察一覧機能 (diagnosis-list)

## 1. UI/ルーティング
- [x] 診察一覧ルート `/diagnoses` を追加
- [x] 初回アクセス時に `exam_date` を当日に自動設定
- [x] `exam_date` 未指定時に当日をURLクエリへ反映
- [x] クエリ `detail` と右スライドパネル（`DiagnosisDetailPanel`、幅約 2/3）
- [x] 行クリックで `detail` 付与・パネルオープン、閉じ完了で `detail` 除去

## 2. APIクライアント
- [x] `GET /api/examinations` のAPIクライアントを利用/追加
- [x] クエリ `exam_date`, `sort_by`, `sort_order`, `patient_id`, `patient_name`, `limit`, `offset` を整備

## 3. ViewModel
- [x] `useDiagnosisList` を実装 (取得/ローディング/エラー)
- [x] `useDiagnosisFilters` を実装（患者ID/氏名の入力値と確定値の分離、Enter 確定）
- [x] `useSortQueryParams` を実装 (URLクエリ同期)
- [x] `useExaminationsSse` を実装（SSE 受信で `examinations` クエリ再取得）

## 4. UIコンポーネント
- [x] `FilterPanel` を実装（検査日/患者ID/氏名、Enter 確定検索）
- [x] `DiagnosisTable` を実装 (ソートUI/選択ハイライト/詳細オープン)
- [x] `DiagnosisDetailPanel` + `ExaminationDetailView` 埋め込み
- [x] `RefreshButton`, `EmptyState`, `ErrorState` を実装

## 5. 表示/振る舞い
- [x] 取得中/失敗/0件の表示
- [x] 初期ソート: 検査日時 降順
- [x] SSE 更新通知/フォーカス再取得

## 6. テスト
- [x] フィルター Enter 確定（IME 変換中 Enter 除外）
- [x] SSE 受信時の一覧再取得
- [x] ソートとクエリ同期
- [x] 0件/エラー/ローディング
- [x] 行選択ハイライト

## 7. 開発ツール（共通）
- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
