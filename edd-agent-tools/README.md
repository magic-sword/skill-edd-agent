# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

## 主な機能

- **CLI 実行ラッパー (`edd_agent_tools.testing.cli`)**: 各スキルスクリプトをCLIから直接実行・テストするための共通ラッパー。
- **モックコンテキスト (`edd_agent_tools.testing.mock_context`)**: テスト・デバッグ用の `MockInvocationContext` を提供。

## スキルレジストリとエントリーポイント規約 (Skill Registry & Entrypoint Convention)

`edd-agent-tools` は、プロジェクト内のスキル（インプロセスツール）やエージェントの動的ロード・管理を司る `SkillRegistry` クラスを提供します。このレジストリシステムは、**「規約による設定 (Convention over Configuration)」** という設定思想に基づいて設計されています。

### 1. 統一エントリーポイント規約 (`scripts/main.py`)
すべてのスキル・エージェントは、実行可能なエントリーポイントとして常に **`scripts/main.py`** を配備しなければなりません。
`SkillRegistry.load_tool("スキル名", "関数名")` が呼び出されると、レジストリは自動的に対象スキルの `scripts/main.py` を動的ロードし、指定された関数オブジェクトを取得します。

### 2. 設計思想：CLIとビジネスロジックの分離
エントリーポイントの統一と、実行コードの分離には以下の決定的な理由があります。

1.  **インポート副作用（Side Effects）の排除**:
    ワークフローや自動テストエンジンがインプロセスでツールを動的インポートする際、CLIのパース処理（`argparse` などの実行）が勝手に走ってしまい、実行時エラーを引き起こす問題（副作用）を防ぎます。
2.  **実行環境の分離**:
    - **CLI経由での独立実行**: `python src/skills/[スキル名]/scripts/main.py --param1 value` のように、常に統一された CLI インターフェースでスキルを独立してテスト・動作確認できます。
    - **インプロセスでのセマンティックな連携**: ワークフロー内では、`main.py` に隔離された CLI 処理を介さず、インプロセス関数（`process_message` など）として副作用なく安全にロードして呼び出せます。

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
