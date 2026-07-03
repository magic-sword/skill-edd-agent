# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

## 主な機能

- **CLI 実行ラッパー (`edd_agent_tools.testing.cli`)**: 各スキルスクリプトをCLIから直接実行・テストするための共通ラッパー。
- **モックコンテキスト (`edd_agent_tools.testing.mock_context`)**: テスト・デバッグ用の `MockInvocationContext` を提供。

## インストール方法

### ローカル開発環境（editable モード）
```bash
pip install -e /workspace/edd-agent-tools
```

### Gitから直接インストール
```bash
pip install git+https://github.com/magic-sword/edd-agent-tools.git
```

---

## パッケージのビルドと公開手順（PyPI / プライベートレジストリ）

将来的に PyPI や Artifact Registry 等へ公開・リリースする際の手順です。

### 1. ビルドツールのインストール
```bash
pip install build twine
```

### 2. パッケージのビルド
プロジェクトのルート（`pyproject.toml` があるディレクトリ）で以下のコマンドを実行し、配布用パッケージを生成します。
```bash
python -m build
```
実行後、`dist/` ディレクトリ内に `.tar.gz` と `.whl` ファイルが生成されます。

### 3. レジストリへのアップロード（公開）

#### PyPI (パブリック) へ公開する場合
```bash
twine upload dist/*
```
※認証情報（APIトークン等）の入力を求められます。

#### プライベートレジストリ（例: Google Cloud Artifact Registry）へ公開する場合
事前にレジストリ設定を終えた後、以下を実行します。
```bash
twine upload --repository-url https://<REGION>-python.pkg.dev/<PROJECT_ID>/<REPOSITORY_NAME>/ dist/*
```
