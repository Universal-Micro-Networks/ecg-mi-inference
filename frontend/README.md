# ECG MI Inference Frontend

React + TypeScript + Vite フロントエンドアプリケーション

## 前提条件

- Node.js 20 以上
- npm 10 以上

### Node.js のインストール

```bash
# macOS (Homebrew)
brew install node@20

# nvm を使う場合
nvm install 20
nvm use 20

# 公式サイトからダウンロード
# https://nodejs.org/
```

## ローカル開発環境のセットアップ

### 1. 依存関係のインストール

```bash
# フロントエンドディレクトリに移動
cd frontend

# 依存関係をインストール
npm install
```

### 2. 環境変数の設定（オプション）

バックエンドAPIのURLをカスタマイズする場合は、`.env.local` ファイルを作成します：

```bash
# .env.local
VITE_API_URL=http://localhost:8000
```

デフォルトでは `http://localhost:8000` が使用されます。

### 3. 開発サーバーの起動

```bash
# 開発サーバーを起動
npm run dev
```

ブラウザで `http://localhost:5173` にアクセスできます。

## アクセス

- **開発サーバー**: `http://localhost:5173`
- **バックエンドAPI**: `http://localhost:8000`（別途起動が必要）

## 利用可能なコマンド

### 開発

```bash
# 開発サーバーを起動（ホットリロード有効）
npm run dev

# 開発サーバーをホストモードで起動（ネットワークアクセス可能）
npm run dev -- --host
```

### ビルド

```bash
# プロダクションビルド
npm run build

# ビルド結果をプレビュー
npm run preview
```

### コード品質

```bash
# ESLintでコードをチェック
npm run lint

# TypeScriptの型チェック
npm run type-check
# または
npx tsc --noEmit
```

### テスト

```bash
# テストを実行（設定が必要）
npm run test

# カバレッジ付きでテスト
npm run test:coverage
```

## プロジェクト構造

```
frontend/
├── public/              # 静的ファイル
├── src/
│   ├── features/        # 機能別コンポーネント
│   │   ├── diagnosis-list/    # 診察一覧画面
│   │   │   ├── components/    # 一覧用コンポーネント
│   │   │   ├── hooks/         # カスタムフック
│   │   │   ├── types.ts       # 型定義
│   │   │   └── DiagnosisListPage.tsx
│   │   └── diagnosis-viewer/  # 診察詳細画面
│   │       ├── components/    # 詳細用コンポーネント
│   │       ├── hooks/         # カスタムフック
│   │       ├── types.ts       # 型定義
│   │       └── DiagnosisViewerPage.tsx
│   ├── App.tsx          # ルートコンポーネント
│   ├── main.tsx         # エントリポイント
│   └── index.css        # グローバルスタイル
├── index.html
├── package.json
├── tsconfig.json        # TypeScript設定
├── vite.config.ts       # Vite設定
└── README.md
```

## 機能

### 診察一覧 (Diagnosis List)

- 検査一覧の表示
- 日付フィルター
- 患者ID・患者名での絞り込み
- カラムごとのソート
- 推論実行

### 診察詳細 (Diagnosis Viewer)

- 検査詳細情報の表示
- ECG画像の表示
- リアルタイム推論実行とポーリング
- 推論結果の表示

## 依存関係の管理

### パッケージの追加

```bash
# 通常の依存関係
npm install <package-name>

# 開発用依存関係
npm install --save-dev <package-name>
```

### パッケージの更新

```bash
# 全パッケージを最新版に更新
npm update

# 特定のパッケージを更新
npm update <package-name>

# メジャーバージョンアップを含む更新
npx npm-check-updates -u
npm install
```

## トラブルシューティング

### ポート5173が既に使用されている

```bash
# vite.config.ts で別のポートを指定
export default defineConfig({
  server: {
    port: 3000  // 任意のポート番号
  }
})
```

または起動時にポートを指定：

```bash
npm run dev -- --port 3000
```

### バックエンドに接続できない

1. バックエンドが起動していることを確認
```bash
curl http://localhost:8000/health
```

2. CORS設定を確認（バックエンド側）

3. `.env.local` で正しいAPIのURLを設定

### npm install が失敗する

```bash
# node_modules と package-lock.json を削除して再インストール
rm -rf node_modules package-lock.json
npm install

# npmのキャッシュをクリア
npm cache clean --force
npm install
```

### TypeScriptエラー

```bash
# 型定義パッケージを再インストール
npm install --save-dev @types/react @types/react-dom

# TypeScriptの型チェックを実行
npx tsc --noEmit
```

## 技術スタック

### コア

- **React 18**: UIライブラリ
- **TypeScript**: 型安全性
- **Vite**: ビルドツール・開発サーバー

### 主要ライブラリ

このプロジェクトでは以下のプラグインを使用しています：

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
