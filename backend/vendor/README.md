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
git -C backend/vendor/mfer-tools checkout main
git -C backend/vendor/mfer-tools pull --ff-only
```

HTTPS で取れない場合は `Makefile` の `MFER_TOOLS_GIT_URL` を `git@github.com:tkwataru/mfer-tools.git` にしてから同じく `make vendor-mfer-tools` してください。

`backend/vendor/mfer-tools/pyproject.toml` があれば `docker compose build backend` が進みます。

リポジトリには `backend/vendor/mfer-tools/.gitkeep` だけが入っており、**未実行のままだとビルドは Dockerfile 内のチェックで失敗**します（`make build` は事前に `pyproject.toml` の有無を確認します）。

## inference_ecg_bnp（ECG→BNP 推論）

非公開リポジトリの場合は `gh auth login` 後に HTTPS で clone できます。

```bash
make vendor-inference-bnp
```

手動の場合:

```bash
rm -rf backend/vendor/inference_ecg_bnp
git clone https://github.com/tkwataru/inference_ecg_bnp.git backend/vendor/inference_ecg_bnp
```

バックエンドでは `cd backend && uv sync` で `inference-ecg-bnp` と PyTorch 群がメイン依存として入る。GitHub に届かない環境では `make vendor-inference-bnp` で `vendor/inference_ecg_bnp/src` を置くフォールバック可。学習済み重みや設定は `set_bnp_inference_config` / 環境変数で渡す（詳細は `backend/README.md`）。

## SSH 認証で Docker ビルドだけ済ませる（vendor 不要）

ホストで `git@github.com` に SSH ログインできるなら、**リポジトリを `backend/vendor` に置かず**、BuildKit が SSH エージェントをビルドに渡して `git+ssh` で `pip install` できます。

```bash
# 例: ssh-agent に鍵を載せていること（Docker BuildKit がホストの SSH エージェントを参照する）
ssh-add -l || ssh-add ~/.ssh/id_ed25519
ssh -T git@github.com

make build-ssh
# または
make dev-ssh
```

`make build-ssh` / `make dev-ssh` は **`docker compose build --ssh default`** を付けます。手動でビルドする場合も同様に `--ssh default` が必要です。

裏では `docker-compose.ssh.yml` が `MFER_TOOLS_INSTALL=ssh` と `build.ssh: [default]` を付与しています。手動なら次と同等です。

```bash
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 \
  docker compose -f docker-compose.yml -f docker-compose.ssh.yml build --ssh default backend
```

### `ssh -T git@github.com` が `Permission denied (publickey)` のとき

GitHub は **公開鍵がアカウントに登録されている**ことと、**接続時にその秘密鍵が使われる**ことが必要です。次を順に確認してください。

1. **鍵ファイルがあるか**（例: `~/.ssh/id_ed25519` と `~/.ssh/id_ed25519.pub`）
   - 無ければ作成: `ssh-keygen -t ed25519 -C "あなたのメール" -f ~/.ssh/id_ed25519`
2. **公開鍵を GitHub に登録**  
   GitHub → Settings → SSH and GPG keys → New SSH key に、`id_ed25519.pub` の内容を貼る。
3. **ssh-agent に秘密鍵を載せる**（macOS ではターミナルごとに必要なことがある）
   - `eval "$(ssh-agent -s)"` のあと `ssh-add --apple-use-keychain ~/.ssh/id_ed25519`  
     （古い OpenSSH では `ssh-add -K`）
4. **どの鍵を使うか明示**（複数鍵や GitHub 以外用の設定がある場合）  
   `~/.ssh/config` に例:

   ```sshconfig
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_ed25519
     IdentitiesOnly yes
   ```

5. **詳細ログ**で原因を切り分け: `ssh -vT git@github.com`  
   `Offering public key` のあと `Authentication succeeded` になるか、`no mutual signature` 等が出ていないかを見る。

**Docker Desktop だけ失敗する**場合は、ビルドを走らせるターミナルで `ssh-add -l` に鍵が出ているか、`make build-ssh` が **`--ssh default`** を付けているかを確認してください。

コミット固定を変えたい場合は、`docker compose ... build --ssh default --build-arg MFER_TOOLS_COMMIT=<ブランチ名またはSHA>` を利用してください（既定は Dockerfile の `main`）。
