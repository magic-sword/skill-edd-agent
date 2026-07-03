# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

## 主な機能

- **CLI 実行ラッパー (`edd_agent_tools.testing.cli.SkillCommandLineRunner`)**: 各スキルスクリプトをCLIから直接実行・テストするための共通ラッパー。
- **モックコンテキスト (`edd_agent_tools.testing.mock_context`)**: テスト・デバッグ用の `MockInvocationContext` を提供。
- **サブプロセス実行コマンド定義 (`edd_agent_tools.testing.command.Command`, `SkillCommand`, `SystemCommand`)**: 起動するスキルや外部コマンドを表すSOLIDなコマンドオブジェクト。
- **サブプロセス実行ランナー (`edd_agent_tools.testing.runner.SubprocessRunner`)**: コマンドをサブプロセスとして安全に起動するランナー。ADKの評価で日本語 Rouge-1 のすり抜けを防止する多言語パッチを自動適用します。

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

---

## 多言語（日本語）テスト実行パッチについて

### 背景と目的
ADK 2.0 が標準で利用している Rouge-1 評価器（`final_response_match_v1`）は、内部でスペース区切り（英語向け）のトークナイザーを使用しているため、日本語のようなスペース区切りのない言語では、テキスト全体が巨大な1トークン扱いとなり、曖昧なマッチングによって「不合格のケースが合格として判定されてしまう（すり抜け）」というバグが発生します。

この問題を解決するため、`edd-agent-tools` には Hugging Face の多言語対応トークナイザー（`bert-base-multilingual-cased`）を `adk eval` や他のスキルの実行プロセスに動的に注入（モンキーパッチ）する仕組みが組み込まれています。

### 仕組み（Monkey Patch のインジェクション）
Python の自動フックファイルである `usercustomize.py` をパッケージ内の `patch/` ディレクトリ配下に定義しています。
後述の `SkillSubprocessRunner` を経由してサブプロセスを実行する際、このパッチディレクトリが自動的に環境変数 `PYTHONPATH` に結合されて起動し、対象プロセス内の `rouge_score` のデフォルトトークナイザーを多言語対応モデルに自動的に上書き・差し替えます。

---

## サブプロセス実行設計 (SubprocessRunner & Commands)

`edd-agent-tools` では、他のスキルや外部のシステムコマンド（`adk eval` 等）を親プロセスから CLI サブプロセスとして実行するために、**「コマンドの定義（データ）」**と**「ランナー（実行環境）」**を分離したオブジェクト指向設計を採用しています。

これにより、すべてのサブプロセス起動時に**自動的に日本語トークナイズパッチ（`PYTHONPATH`）が適用**されます。

### 主要クラス
- **`SubprocessRunner`**: コマンドオブジェクト（`Command`）を受け取り、環境変数を自動補正した上でサブプロセスとして安全に実行するランナー。
- **`SkillCommand`**: 登録されたスキル（例: `test-executor`）を起動するためのコマンドクラス。スキルのエントリーポイント（`scripts/main.py`）をレジストリから自動解決します。
- **`SystemCommand`**: 外部のシステムコマンド（例: `adk`）を起動するためのコマンドクラス。

### 使用方法

#### 1. 外部システムコマンド（例: `adk eval`）を実行する場合
```python
from edd_agent_tools.testing import SystemCommand, SubprocessRunner

# 1. 外部コマンドと引数を定義
cmd = SystemCommand("adk", args=["eval", "/workspace/src", "/workspace/src/tests/..."])

# 2. ランナーに渡して実行
runner = SubprocessRunner(cmd)
result = runner.run(
    env={
        "HOME": "/home/vscode",
        "GEMINI_API_KEY": "...",
    }
)

print(result.stdout)
```

#### 2. 他のスキルをサブプロセスとして実行する場合
```python
from edd_agent_tools.testing import SkillCommand, SubprocessRunner

# 1. スキル起動用の引数と入力データを定義
cmd = SkillCommand(
    "test-executor",
    args=["--eval_mode", "1", "--threshold_accuracy", "1.0"],
    input_data={
        "skill_name": "skill-evaluator",
        "eval_set_path": "path/to/evalset.json"
    }
)

# 2. ランナーに渡して実行（自動で main.py が解決されます）
runner = SubprocessRunner(cmd)
result = runner.run()

print(result.stdout)
```
