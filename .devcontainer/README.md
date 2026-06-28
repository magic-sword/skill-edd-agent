# Agents CLI & ADK 2.0 Dev Container テンプレート

このリポジトリは、Google の Agents CLI と ADK 2.0 (Agent Development Kit) を用いたエージェント開発環境を、Antigravity IDEから簡単にアタッチして利用するためのテンプレートです。

## 特徴

- **Python 3.14 / uv 搭載**: 高速なパッケージマネージャである `uv` と、最新の安定版 Python 3.14 をサポートしています。
- **Agents CLI & SDK プリインストール**: コンテナのシステム Python環境に `google-agents-cli` があらかじめインストールされており、コンテナ起動直後から `agents-cli` コマンドや `import google.genai` がそのまま使用可能です。
- **.venv 構築不要**: 必要なライブラリはすべてコンテナ内のシステム環境に直接配置されるため、仮想環境 (`.venv`) をローカルに作成・構築・マウントする手間が一切ありません。ホストOS（Windows等）との競合も発生しません。
- **gcloud CLI 搭載**: Google Cloud 連携のための CLI を同梱。ホストマシンの認証情報が自動的に共有されます。
- **グローバルルールの自動共有**: ホスト側のGeminiグローバルルール設定ディレクトリ（`~/.gemini/config`）がコンテナ内の `/home/vscode/.gemini/config` に自動的にマウントされ、設定なしでそのまま共有されます。
- **MIT-0 ライセンス**: 著作権表記不要で、どなたでも自由に改変・コピー・再配布いただけます。

## 親プロジェクトへの導入手順

この環境を既存または新規の Python プロジェクトの `.devcontainer` として利用するには、親プロジェクトのルートディレクトリで以下のコマンドを実行し、Git サブモジュールとして追加します。

```bash
git submodule add <GitHubリポジトリのURL> .devcontainer
git submodule update --init --recursive
```

これにより、親プロジェクトの `.devcontainer/` 以下に本テンプレートの構成ファイルが配置されます。

## 事前準備

この開発環境を利用するには、ホストマシンに以下が準備されている必要があります：

1. **Docker Desktop** (または WSL 2 等の Docker ランタイム)
2. **Antigravity IDE**

## 利用手順

### 1. コンテナの起動
ホストマシンのターミナル（PowerShellやBashなど）で、親プロジェクトのルートディレクトリ（`.devcontainer`の親フォルダ）に移動し、以下のコマンドを実行してコンテナを起動します。

```bash
docker compose -f .devcontainer/docker-compose.yml up -d
```

### 2. Antigravity IDE でプロジェクトを開く
親プロジェクトのフォルダを Antigravity IDE で開きます。

### 3. コンテナへのアタッチ
Antigravity IDEの統合ターミナル、またはホストマシンのターミナルから以下のコマンドを実行して、コンテナ内のシェルにアタッチします。

```bash
docker compose -f .devcontainer/docker-compose.yml exec app bash
```

### 4. 依存パッケージの同期とADK of 初期セットアップ
コンテナに初めてアタッチした際、または依存関係を更新した際は、コンテナ内で以下のコマンドを実行して環境をセットアップします。

```bash
# 依存パッケージがある場合、コンテナのシステム環境にインストール
if [ -f requirements.txt ]; then
  uv pip install --system -r requirements.txt
elif [ -f pyproject.toml ]; then
  uv pip install --system -e .
fi

# Agents CLIのセットアップを実行（ADKの仕様がエージェントに読み込まれます）
uvx google-agents-cli setup --skip-auth
```

### 5. Agents CLI の利用
セットアップ完了後、コンテナ内で `agents-cli` コマンドを実行して、エージェントの作成やテストを開始できます。

```bash
agents-cli --help
```

### 6. Google Cloud の認証
Google Cloud の認証は、コンテナ内（アタッチしたターミナル）で実行します。

```bash
gcloud auth login
```

ログイン完了後、以下のコマンドで認証されたアカウントがアクティブになっていることを確認できます。

```bash
gcloud auth list
```

---

## 環境変数と機密情報の管理 (.env)

API キーやプロジェクトIDなどの環境変数は、プロジェクトのルートディレクトリ（`.devcontainer`の親フォルダ）に配置する `.env` ファイル、またはホストマシンの環境変数を通じてコンテナに自動的に引き継がれます。

### 1. 基本設定 (.env ファイルの作成)
テンプレートに含まれる `.env.example` を親プロジェクトのルートにコピーして `.env` ファイルを作成します。

```bash
cp .devcontainer/.env.example .env
```

### 2. 複数プロジェクト並行起動時のコンテナ名衝突防止
複数のプロジェクトでこのコンテナを並行して起動する場合、コンテナ名が重複すると起動エラーになります。
作成した `.env` ファイルの `COMPOSE_PROJECT_NAME` 変数にプロジェクト固有の名前を設定してください。コンテナ名が `[プロジェクト名]-app` として構築され、名前の衝突を回避できます（未設定の場合は親ディレクトリ名がデフォルトとして使用されます）。

```ini
COMPOSE_PROJECT_NAME=my-unique-agent-project
```

### 3. 機密情報の管理 (推奨される安全な方法)
`GEMINI_API_KEY` などのAPIキー（機密情報）を `.env` ファイルに直接書き込むと、誤って Git などのバージョン管理システムにコミットしてしまう危険性があります。

そのため、**機密情報はホストマシン（ご自身のPC）の環境変数に設定し、それをコンテナに引き継ぐ方法を強く推奨します。**

#### 設定手順：

1. **ホストマシン側で環境変数を設定します。**
   - **Windows (PowerShell) の場合**:
     ```powershell
     [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-actual-api-key', 'User')
     # 設定を反映させるため、Antigravity IDEを一度完全に再起動してください
     ```
   - **Mac / Linux / WSL (bash/zsh) の場合**:
     `~/.bashrc` や `~/.zshrc` に以下を追記します。
     ```bash
     export GEMINI_API_KEY="your-actual-api-key"
     ```

2. **`.env` ファイルには引き継ぎ用の記述をします。**
   作成した `.env` ファイル内で、以下のように環境変数名をプレースホルダー表記にします。
   ```ini
   GEMINI_API_KEY=${GEMINI_API_KEY}
   GCP_PROJECT_ID=your-gcp-project-id
   ```
   手動起動などの Docker Compose 起動時にホストマシンの環境変数 `GEMINI_API_KEY` の値がコンテナ内に安全に注入されます。

---

## グローバルルールの共有

ホスト側のユーザーディレクトリ下にある Gemini のグローバルルール設定（`~/.gemini/config`）は、Docker Composeのボリュームマウントによってコンテナ内の `/home/vscode/.gemini/config` に自動的に共有されます。

これにより、コンテナ内にアタッチした Antigravity IDE のエージェント（`agents-cli`）も、ホスト側で定義されたグローバルルール（`GEMINI.md` や `AGENTS.md` など）を自動的に認識して動作します。手動でのパス指定や追加の設定は不要です。

---

## WSL 2 / Docker Desktop on Windows に関する注意事項

コンテナを WSL 2 (Windows Subsystem for Linux) が有効な Docker Desktop on Windows 上に構築する場合、以下の点に注意してください。

### 1. プロジェクトの配置場所の推奨（パフォーマンスとパーミッションの最適化）
Windowsのファイルシステム上（`/mnt/c/...` や `C:\Users\...` などのパス）にプロジェクトディレクトリを置いたままコンテナにバインドマウントすると、ディスクI/Oパフォーマンスが著しく低下し、ファイルの変更監視が正常に動かない、あるいはパーミッションエラー（実行権限の不足など）が発生する原因となります。

- **推奨**: プロジェクトディレクトリは、WSL 2のLinuxファイルシステム内（例：`\\wsl$\Ubuntu\home\<ユーザー名>\` や WSLターミナル上の `~/`）に配置し、そこから Antigravity IDE で開いて起動することを強く推奨します。

### 2. コンテナ起動コマンドの実行場所
WSL 2を使用している場合は、WindowsのPowerShellからではなく、WSLのターミナル（Ubuntu等）内から `docker compose` コマンドを実行して起動することをお勧めします。これにより、マウント時のファイルパス解決やパーミッションの問題をほぼすべて回避できます。
