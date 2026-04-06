# タスク一覧: 診察一覧機能 (diagnosis-list)

## 1. UI/ルーティング
- [x] 診察一覧ルート `/diagnoses` を追加
- [x] 初回アクセス時に `exam_date` を当日に自動設定
- [x] `exam_date` 未指定時に当日をURLクエリへ反映

## 2. APIクライアント
- [x] `GET /api/examinations` のAPIクライアントを利用/追加
- [x] クエリ `exam_date`, `sort_by`, `sort_order`, `patient_id`, `patient_name`, `limit`, `offset` を整備

## 3. ViewModel
- [x] `useDiagnosisList` を実装 (取得/ローディング/エラー)
- [x] `useDiagnosisFilters` を実装 (患者ID/氏名, 500msデバウンス)
- [x] `useSortQueryParams` を実装 (URLクエリ同期)
- [x] `useRowSelection` を実装 (行選択)

## 4. UIコンポーネント
- [x] `FilterPanel` を実装 (検査日/患者ID/氏名/クリア/更新)
- [x] `DiagnosisTable` を実装 (ソートUI/選択ハイライト)
- [x] `RefreshButton`, `EmptyState`, `ErrorState` を実装

## 5. 表示/振る舞い
- [x] 取得中/失敗/0件の表示
- [x] 初期ソート: 検査日時 降順
- [x] 手動リフレッシュ/フォーカス再取得

## 6. テスト
- [x] フィルター/クリア/デバウンス（サーバー検索へのデバウンス適用）
- [x] ソートとクエリ同期
- [x] 0件/エラー/ローディング
- [x] 行選択ハイライト

## 7. 開発ツール（共通）
- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
