# 設計書: 診察詳細表示機能 (diagnosis-viewer)

## 目的
診察一覧と同一画面内の**右スライドパネル**で、患者情報・心電図・診察メタ情報（折りたたみ）を表示し、**判定 FAB＋モーダル**で推論結果の確認・実行・クリップボードコピーを行う。

## 画面 / ルーティング
- **詳細の開き方:** 一覧ルート `/diagnoses` 上でクエリ **`detail=<診察UUID>`** を付与する（フィルタ・ソート・ページング等の他クエリと併存）
- **レガシー:** `/diagnoses/:id` は **`/diagnoses?detail=<id>`** へ `Navigate`（`DiagnosisLegacyRedirect`）
- **全画面の診察詳細ルートは用いない**（`ExaminationDetailView` はパネル内専用）

## 親子関係（diagnosis-list）
- `DiagnosisListPage`: `detail` クエリ、`renderId` / `panelOpen`（URL とアニメーションの分離）、`DiagnosisDetailPanel` をマウント
- `DiagnosisDetailPanel`: 全画面オーバーレイ、右 `aside`（幅 **約 `calc(100vw * 2/3)`**、狭幅ブレークポイントで全幅）、`transform` でスライド、`aria-label="診察詳細"`
- `ExaminationDetailView`: 実コンテンツ（ヘッダー見出し・× なし）

## API 設計
- `GET /api/examinations/{id}`
  - Response: 診察詳細（患者、`mfer_file_path`、`csv_file_path`、`created_at`、推論サマリ等）
- `POST /api/examinations/{id}/export-wave-csv`
  - 認可: JWT 必須
  - 処理: `.mwf` 解決 → `mfer_tools.extract_mfer_data` + `save_wave_csv` → `data/waves/{id}.csv`、`csv_file_path` 更新、ECG PNG キャッシュ無効化
  - Response: 更新後の `csv_file_path` 等
- `GET /api/examinations/{id}/ecg-image`
  - Response: `image/png`
  - 処理: `ecg_service` が CSV の `time` と標準 12 誘導名列を読み、matplotlib で **6 行 × 2 列**サブプロットの 1 枚 PNG を生成（I/V1, II/V2, III/V3, aVR/V4, aVL/V5, aVF/V6）。欠損誘導はプレースホルダ。単一数値列のみは誘導 II。CSV が読めない・利用可能な誘導がない場合は **`EcgWaveformLoadError`** とし API は **422**（デモ用合成波形は返さない）
  - 拡張: `?lead=<標準12誘導名>` 指定時は単誘導 PNG を返す（不正 lead は 400）
  - 解像度: 12誘導全体表示と単誘導表示で別 DPI を許容（単誘導は高解像度）
  - スケール/グリッド: 心電図用紙スケール（25mm/s, 10mm/mV）相当として `0.04/0.20秒` と `0.1/0.5mV` の minor/major グリッドを描画
  - 校正波: 1mV・0.2秒の矩形校正波を描画
  - 表示調整: 波形は黒線・細線。軸目盛り数字は非表示（グリッドのみ表示）
  - 単誘導縦スケール: 12誘導の左右列グループ（左: I/II/III/aVR/aVL/aVF, 右: V1-6）ごとに統一
  - **12誘導一覧の縦軸（実装）**: `ecg_service._ylim_for_lead_group` で列ごとの min/max＋パディングを 500µV（大マス）境界に丸め、`sharey="col"` の各列 6 パネルへ `set_ylim` してから `_draw_calibration_pulse` を実行する。単誘導 PNG は同関数を再利用し、一覧と拡大で校正波の有無が食い違わないようにする
  - キャッシュ: `data/ecg_cache/`、`_ECG_CACHE_VERSION`（例: `v9-12lead-column-ylim-cal`）でレイアウト・縦軸規則変更時に無効化。フロントは `useEcgImage` の `cacheKey` で `?v=` バイパス
- `POST /api/inferences` / `GET /api/inferences/{id}`（推論 UUID または**診察 UUID**＝その最新推論。完了レスポンスに `risk_level` / `risk_score` / `executed_at` を含む）
- 推論エンジン未接続時はバックエンドモック: 同一診察で実行するたび **高（陽性 UI）／低（陰性 UI）** が交互、完了まで約 0.45 秒
- 認可: JWT

## フロントエンド設計

### コンポーネント構成
- `ExaminationDetailView` — パネル本文
- `PatientInfoCard` — 横一列（`patient-info-row`）
- `EcgImagePanel` — `<img>`、セクション見出しなし。12誘導画像クリックで全画面ビューア（単誘導表示、誘導切替、+/-ズーム、ドラッグ移動）
- `ExaminationInfoCard` — `collapsible` 時 `<details>`、初期閉、サマリー「詳細」
- `JudgmentModal` — 判定結果・実行中・未実行・エラー、`data-prevent-panel-escape`
- `ConfirmDialog` — 推論実行確認（同上属性でパネル Escape 抑止）
- （削除済・参照しない）`DiagnosisViewerPage`、`BackToListButton`、`InferenceResultPanel`

### ViewModel (Hooks)
- `useDiagnosisDetail` — 診察詳細取得
- `useEcgImage(examinationId, cacheKey)` — blob / Object URL、`cacheKey` で再取得
- `useInference` — 推論実行、実行中ポーリング（現状約 800ms／モック向け）

### 状態管理
- サーバー状態: TanStack Query
- 推論ポーリング: ステータス「実行中」のみ `refetchInterval`

## 表示仕様（パネル内）
- `viewer-page--embedded` 配下の `.card` は **背景・枠・影をオーバーライド**しフラット化
- 心電図 `<img>` は枠線なし
- パネル本体では静的表示のみ（ズーム/パンは全画面ビューア内に限定）
- 縦並び順: **患者 → 心電図 → 詳細（折りたたみ）**
- 右下固定 **判定 FAB**（`judgment-fab`）、下余白でコンテと干渉回避

## 判定モーダル（`JudgmentModal`）
- **完了 ×（高｜中）:** 陽性 UI（ピンク円＋警告三角、指定文言）
- **完了 × 低:** 陰性 UI（緑円＋チェック、指定文言）
- **その他完了:** スコア・レベル・日時の要約
- **未実行:** 説明＋「推論を実行」→ `ConfirmDialog`
- **実行中:** スピナー＋文言
- **エラー:** 警告見た目＋メッセージ
- フッター: 完了時 **コピー**（`navigator.clipboard`）＋**閉じる**；未実行時 **推論を実行**＋**閉じる**
- Escape / バックドロップで閉じる

## MFER → 波形 CSV
- ボタンは `ExaminationInfoCard` の折りたたみ内

## エラーハンドリング
- API 失敗: メッセージ表示（モーダルまたはパネル）
- 認可失敗: ログインへリダイレクト

## テスト方針
- 詳細取得の成功/失敗/不存在
- 推論確認ダイアログ → 実行 → モーダル表示更新
- 心電図画像の表示/エラー
- `ecg_service` 多誘導 CSV / 単列 CSV（バックエンド）
- 波形 CSV エクスポート API

## 非機能
- 診察詳細取得: 2 秒以内目標
- 心電図画像: 3 秒以内目標

---

**最終更新:** 2026-04-08（12誘導一覧の列別 `set_ylim` と校正波の整合）
