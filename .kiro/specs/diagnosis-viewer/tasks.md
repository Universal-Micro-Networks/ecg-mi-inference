# タスク一覧: 診察詳細表示機能 (diagnosis-viewer)

## 1. ルーティング/取得
- [ ] 診察詳細ルート `/diagnoses/:id` を追加
- [ ] `GET /api/examinations/{id}` で詳細取得

## 2. 心電図画像
- [ ] `GET /api/examinations/{id}/ecg-image` を利用
- [ ] 画像取得 (blob) とURL生成
- [ ] 読み込み中/取得失敗/画像なしの表示
- [ ] `Cache-Control` / `ETag` を尊重した再取得方針を実装

## 3. 推論
- [ ] 推論実行 `POST /api/inferences`
- [ ] 推論ステータス取得 `GET /api/inferences/{examination_id}`
- [ ] ステータスに応じた表示/ボタン制御
- [ ] 5秒間隔のポーリング (実行中のみ)

## 4. UIコンポーネント
- [ ] `DiagnosisViewerPage` を実装
- [ ] `PatientInfoCard` / `ExaminationInfoCard`
- [ ] `InferenceResultPanel`
- [ ] `EcgImagePanel`
- [ ] `BackToListButton`
- [ ] `ConfirmDialog`

## 5. 表示/振る舞い
- [ ] ローディング/エラー/不存在
- [ ] 推論中ボタン無効化

## 6. テスト
- [ ] 詳細取得の成功/失敗/不存在
- [ ] 推論実行の確認ダイアログ
- [ ] 推論中ポーリング停止条件
- [ ] 心電図画像の表示/エラー
- [ ] 画面フォーカス復帰時の再取得

## 7. 開発ツール（共通）
- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
