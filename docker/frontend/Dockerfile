# Frontend Dockerfile (Development)
# React + TypeScript + Vite

FROM node:20-alpine

# 作業ディレクトリを設定
WORKDIR /app

# パッケージマネージャーのキャッシュを有効化
RUN npm config set cache /root/.npm --global

# package.jsonとpackage-lock.jsonをコピー（依存関係のインストールを最適化）
COPY frontend/package*.json ./

# 依存関係をインストール（package-lock.jsonが存在する場合はnpm ci、ない場合はnpm install）
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# アプリケーションコードをコピー（開発時はボリュームマウントで上書きされる）
COPY frontend/ .

# 開発サーバーのポートを公開
EXPOSE 5173

# 開発サーバーを起動（ホスト0.0.0.0でバインドしてコンテナ外からアクセス可能に）
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
