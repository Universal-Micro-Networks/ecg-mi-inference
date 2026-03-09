# タスク一覧: 診察一覧機能 (diagnosis-list)

## 1. UI/ルーティング
- [ ] 診察一覧ルート `/diagnoses` を追加
- [ ] 初回アクセス時に `exam_date` を当日に自動設定
- [ ] `exam_date` 未指定時に当日をURLクエリへ反映

## 2. APIクライアント
- [ ] `GET /api/examinations` のAPIクライアントを利用/追加
- [ ] クエリ `exam_date`, `sort_by`, `sort_order` を整備

## 3. ViewModel
- [ ] `useDiagnosisList` を実装 (取得/ローディング/エラー)
- [ ] `useDiagnosisFilters` を実装 (患者ID/氏名, 500msデバウンス)
- [ ] `useSortQueryParams` を実装 (URLクエリ同期)
- [ ] `useRowSelection` を実装 (行選択)

## 4. UIコンポーネント
- [ ] `FilterPanel` を実装 (検査日/患者ID/氏名/クリア/更新)
- [ ] `DiagnosisTable` を実装 (ソートUI/選択ハイライト)
- [ ] `RefreshButton`, `EmptyState`, `ErrorState` を実装

## 5. 表示/振る舞い
- [ ] 取得中/失敗/0件の表示
- [ ] 初期ソート: 検査日時 降順
- [ ] 手動リフレッシュ/フォーカス再取得

## 6. テスト
- [ ] フィルター/クリア/デバウンス
- [ ] ソートとクエリ同期
- [ ] 0件/エラー/ローディング
- [ ] 行選択ハイライト

## 7. 開発ツール（共通）
- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
