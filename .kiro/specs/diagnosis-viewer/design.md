# 設計書: 診察詳細表示機能 (diagnosis-viewer)

## 目的
診察詳細 (患者情報・診察情報・心電図・推論結果) を一画面で表示し、必要に応じて推論を実行する。

## 画面/ルーティング
- 画面: 診察詳細
- ルート: `/diagnoses/:id`
- パラメータ: `id` = 診察ID (UUID)

## API設計
- `GET /api/examinations/{id}`
  - Response: 診察詳細（患者情報、`mfer_file_path`、`csv_file_path`、`created_at`、推論サマリ等）
- `POST /api/examinations/{id}/export-wave-csv`
  - 認可: JWT 必須
  - 処理: DB / `notes` から `.mwf` を解決し、`mfer_tools.extract_mfer_data` + `save_wave_csv` で `data/waves/{id}.csv` に保存、`csv_file_path` 更新、ECG PNG キャッシュ無効化
  - Response: 更新後の診察フィールド（少なくとも `csv_file_path`）
- `GET /api/examinations/{id}/ecg-image`
  - Response: `image/png`
  - 処理: CSVから心電図波形画像を生成して返却
  - キャッシュ: サーバー側で生成結果をキャッシュ（クエリ `?v=` でクライアント側バイパス可能）
- `POST /api/inferences`
  - Body: `{ "examination_id": "..." }`
  - Response: 推論ステータス
- `GET /api/inferences/{examination_id}`
  - 推論ステータス取得 (診察ID単位)
- 認可: JWTをヘッダーに付与

## フロントエンド設計

### コンポーネント構成
- `DiagnosisViewerPage`
- `PatientInfoCard`
- `ExaminationInfoCard`
- `InferenceResultPanel`
- `EcgImagePanel`
- `BackToListButton`
- `ConfirmDialog`

### ViewModel (Hooks)
- `useDiagnosisDetail`
  - 診察詳細取得
- `useEcgImage(examinationId, cacheKey)`
  - 画像取得（blob）と Object URL 生成。`cacheKey !== 0` のとき `ecg-image?v=...` を付与し CSV 再生成後の再取得に対応
- `useInference`
  - 推論実行、ポーリング管理
- 詳細ページ（`DiagnosisViewerPage`）
  - `export-wave-csv` のミューテーション、成功時に詳細クエリ無効化と `cacheKey` インクリメント

### 状態管理
- サーバー状態: TanStack Query
- 推論ポーリング: `refetchInterval` をステータスに応じて切替

## 表示仕様
- 取得中: ローディング表示
- 取得失敗: エラー表示
- 存在しない: 「診察データが見つかりません」
- 推論ステータスに応じて表示を切替
- 推論中は「推論実行」ボタンを無効化

## 心電図画像
- APIで生成した画像を `<img>` で表示
- 読み込み中はローディング
- 画像なし/取得失敗時はメッセージ表示
- MFER から CSV 再出力後は `useEcgImage` の `cacheKey` を変えて再フェッチ

## MFER → 波形 CSV（診察情報カード）
- `ExaminationInfoCard`: エクスポートボタン、MFER/CSV パス表示、API エラー表示

## 推論ポーリング
- ステータスが「実行中」の間のみ 5秒間隔で再取得
- 「完了」または「エラー」で停止

## エラーハンドリング
- API失敗: エラーメッセージ
- 認可失敗: ログイン画面へリダイレクト

## テスト方針
- 詳細取得の成功/失敗/不存在
- 推論実行の確認ダイアログ
- 推論中のポーリング停止条件
- 心電図画像の表示/エラー表示
- 波形 CSV エクスポート API（バックエンド単体テストでモック）

## 非機能
- 診察詳細: 2秒以内
- 心電図画像取得: 3秒以内
- 推論結果表示: 1秒以内
