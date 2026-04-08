# vendor（Docker バックエンド用）

## mfer-tools

`mfer-tools` が **非公開**のため、Docker ビルド内では `git clone` できません。  
このマシンで GitHub にアクセスできる前提で、次を **ビルド前に一度**実行してください。

```bash
make vendor-mfer-tools
```

手動の場合:

```bash
rm -rf backend/vendor/mfer-tools
git clone https://github.com/tkwataru/mfer-tools.git backend/vendor/mfer-tools
git -C backend/vendor/mfer-tools checkout 1012d5ce92ea3279eab975716d6314c8708894b2
```

HTTPS で取れない場合は `Makefile` の `MFER_TOOLS_GIT_URL` を `git@github.com:tkwataru/mfer-tools.git` にしてから同じく `make vendor-mfer-tools` してください。

`backend/vendor/mfer-tools/pyproject.toml` があれば `docker compose build backend` が進みます。

リポジトリには `backend/vendor/mfer-tools/.gitkeep` だけが入っており、**未実行のままだとビルドは Dockerfile 内のチェックで失敗**します（`make build` は事前に `pyproject.toml` の有無を確認します）。

## SSH 認証で Docker ビルドだけ済ませる（vendor 不要）

ホストで `git@github.com` に SSH ログインできるなら、**リポジトリを `backend/vendor` に置かず**、BuildKit が SSH エージェントをビルドに渡して `git+ssh` で `pip install` できます。

```bash
# 例: ssh-agent に鍵を載せていること
ssh -T git@github.com

make build-ssh
# または
make dev-ssh
```

裏では `docker-compose.ssh.yml` が `MFER_TOOLS_INSTALL=ssh` と `build.ssh: [default]` を付与しています。手動なら次と同等です。

```bash
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 \
  docker compose -f docker-compose.yml -f docker-compose.ssh.yml build backend
```

コミット固定を変えたい場合は `docker-compose.ssh.yml` の `build.args` に `MFER_TOOLS_COMMIT` を追加するか、`docker compose build --build-arg MFER_TOOLS_COMMIT=...` を利用してください。
