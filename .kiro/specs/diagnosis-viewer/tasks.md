# タスク一覧: 診察詳細表示機能 (diagnosis-viewer)

## 1. ルーティング/取得

- [x] 一覧上のスライドパネル + クエリ `detail`（`/diagnoses?detail=<UUID>`）
- [x] レガシー `/diagnoses/:id` → `?detail=` リダイレクト（`DiagnosisLegacyRedirect`）
- [x] `GET /api/examinations/{id}` で詳細取得

## 2. 心電図画像

- [x] `GET /api/examinations/{id}/ecg-image` を利用
- [x] バックエンド: CSV 多列対応の **12誘導 6行×2列 グリッド PNG**（`ecg_service`、キャッシュ版キー更新）
- [x] バックエンド: `GET /api/examinations/{id}/ecg-image?lead=` で単誘導 PNG を返却
- [x] バックエンド: 12誘導表示 / 単誘導表示で DPI 設定を分離
- [x] バックエンド: 心電図用紙スケール相当のグリッド（0.04/0.20秒, 0.1/0.5mV）を適用
- [x] バックエンド: 1mV・0.2秒の校正波を描画
- [x] バックエンド: 12誘導一覧でも単誘導と同一の `_ylim_for_lead_group` で列別 `set_ylim` してから校正波を描画（`v9` キャッシュキー）
- [x] バックエンド: 波形を黒色・細線に調整
- [x] バックエンド: 軸目盛り数字を非表示化（グリッドは維持）
- [x] バックエンド: 単誘導の縦スケールを左右列グループ単位で統一
- [x] 画像取得 (blob) とURL生成
- [x] 読み込み中/取得失敗/画像なしの表示
- [x] 再取得方針: クエリ `?v={cacheKey}` によるキャッシュバイパス（`useEcgImage`）
- [x] フロント: 12誘導画像クリックで全画面ビューアを開く
- [x] フロント: ビューア内で誘導切替、+/-ズーム、ドラッグ移動

## 3. MFER → 波形 CSV 再出力

- [x] `POST /api/examinations/{id}/export-wave-csv`（バックエンド）
- [x] 診察情報（折りたたみ「詳細」内）にエクスポート操作・パス表示・エラー表示
- [x] 成功時: 詳細クエリ無効化 + `cacheKey` 更新で ECG 画像を再取得

## 4. 推論

- [x] 推論実行 `POST /api/inferences`
- [x] 推論ステータス取得 `GET /api/inferences/{id}`（推論 UUID に加え**診察 UUID**でも最新レコードを解決）
- [x] 判定モーダル（`JudgmentModal`）での結果表示・未実行時実行・クリップボードコピー
- [x] 実行中のみステータスポーリング（現状 **約 800ms**／モック完了が速いため。本番の長時間推論では要件の数秒間隔へ変更可）
- [x] 推論ライブラリ未接続時のモック: 同一診察で「推論を実行」するたび **リスクあり（高）／リスクなし（低）** が交互（`inference_service`、約 0.45s で完了）

## 5. UIコンポーネント

- [x] `ExaminationDetailView`（パネル内・フラット UI）
- [x] `PatientInfoCard`（横一列） / `ExaminationInfoCard`（折りたたみ対応）
- [x] `JudgmentModal` / `ConfirmDialog`
- [x] `EcgImagePanel`
- [x] （一覧側）`DiagnosisDetailPanel`

## 6. 表示/振る舞い

- [x] ローディング/エラー/不存在
- [x] 推論中ボタン無効化

## 7. テスト

- [ ] 詳細取得の成功/失敗/不存在（フロント E2E / 結合）
- [ ] 推論実行の確認ダイアログ
- [ ] 推論中ポーリング停止条件
- [ ] 心電図画像の表示/エラー（紙スケール・校正波・目盛り非表示の目視確認を含む）
- [ ] 単誘導全画面ビューア（誘導切替、ズーム、ドラッグ移動、左右列グループ縦スケール）
- [ ] 画面フォーカス復帰時の再取得
- [x] 波形 CSV エクスポート API（`backend/tests/test_mfer_wave_export.py`）
- [x] `ecg_service` 列別縦軸・校正（`backend/tests/test_ecg_service.py` の `_ylim_for_lead_group` 等）

## 8. 開発ツール（共通）

- [x] pre-commit導入（gitleaks / biome / ruff / pyright）
