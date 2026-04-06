# タスク一覧: 診察詳細表示機能 (diagnosis-viewer)

## 1. ルーティング/取得

- [x] 診察詳細ルート `/diagnoses/:id` を追加
- [x] `GET /api/examinations/{id}` で詳細取得

## 2. 心電図画像

- [x] `GET /api/examinations/{id}/ecg-image` を利用
- [x] 画像取得 (blob) とURL生成
- [x] 読み込み中/取得失敗/画像なしの表示
- [x] 再取得方針: クエリ `?v={cacheKey}` によるキャッシュバイパス（`useEcgImage`）

## 3. MFER → 波形 CSV 再出力

- [x] `POST /api/examinations/{id}/export-wave-csv`（バックエンド）
- [x] 詳細画面の診察情報カードにエクスポート操作・パス表示・エラー表示
- [x] 成功時: 詳細クエリ無効化 + `cacheKey` 更新で ECG 画像を再取得

## 4. 推論

- [x] 推論実行 `POST /api/inferences`
- [x] 推論ステータス取得 `GET /api/inferences/{examination_id}`
- [x] ステータスに応じた表示/ボタン制御
- [x] 5秒間隔のポーリング (実行中のみ)

## 5. UIコンポーネント

- [x] `DiagnosisViewerPage` を実装
- [x] `PatientInfoCard` / `ExaminationInfoCard`
- [x] `InferenceResultPanel`
- [x] `EcgImagePanel`
- [x] `BackToListButton`
- [x] `ConfirmDialog`

## 6. 表示/振る舞い

- [x] ローディング/エラー/不存在
- [x] 推論中ボタン無効化

## 7. テスト

- [ ] 詳細取得の成功/失敗/不存在（フロント E2E / 結合）
- [ ] 推論実行の確認ダイアログ
- [ ] 推論中ポーリング停止条件
- [ ] 心電図画像の表示/エラー
- [ ] 画面フォーカス復帰時の再取得
- [x] 波形 CSV エクスポート API（`backend/tests/test_mfer_wave_export.py`）

## 8. 開発ツール（共通）

- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
