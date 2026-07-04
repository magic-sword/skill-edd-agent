---
name: skill-spec-writer
description: 設計パラメータとソースコードを解析し、Google ADK 2.0互換の仕様書を生成するスキル。
---

# skill-spec-writer

## 概要

このスキルは、Google ADK 2.0 互換の仕様書（SKILL.md や WORKFLOW.md など）を自動生成するための専門ツールです。与えられた設計パラメータ（target_type, name, design_path, source_code_path, output_dir）と、必要に応じて実装コードの内容を詳細に解析します。解析結果に基づき、スキルやワークフローの目的、具体的な機能、入出力インターフェース、依存関係、トリガー条件などを抽出し、人間（開発者）と機械（LLM）の両方にとって理解しやすい形式で整形されたドキュメントとして出力します。これにより、開発者は手動でのドキュメント作成にかかる時間と労力を大幅に削減し、常に最新かつ正確な仕様書を維持することが可能になります。特に、LLMがツールとして利用する際のコンテキスト汚染を最小限に抑えるための簡潔な要約も自動生成されます。

## トリガー条件

- このスキルの仕様書を生成して
- skill-spec-writer のドキュメントを作成して
- 設計情報からSKILL.mdを生成してほしい
- 指定されたパスの設計とコードから仕様書を書いて
- 新しいスキルの仕様書を自動作成して

## AIエージェント向け使用方法

このスキルは、インプロセス（Python関数のロード）およびサブプロセス（`run_skill_script`によるCLI実行）の双方の実行モードをサポートします。

### 1. インプロセス呼び出し (Python API)
ワークフローや他の親エージェントから直接ロードして呼び出す場合は、以下のインターフェースを使用します。

* **ロード関数名**: `process_message`
* **入力状態 (`tool_context.state`)**:
  * スキルのパラメータが直接状態（キー/値）として設定されます。
* **出力状態 (`tool_context.state`)**:
  * 処理の成否や結果データが直接状態に書き込まれます。

### 2. サブプロセス呼び出し (CLI)
* **実行ファイル**: `scripts/main.py`
* **引数 (`args`)**:
  * `input_json`: パラメータ情報を含む JSON 文字列
  * `output_json`: 結果を一時保存するファイルパス

### 3. 出力形式の要件 (Output Mode)

- **Output Mode: CONVERSATIONAL**
  仕様書の生成が完了したことをユーザーに伝え、生成されたファイルのパスを案内します。エラーが発生した場合は、その旨を具体的に伝えます。

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| target_type | str | はい | 対象の種類（'skill' または 'workflow'） |
| name | str | はい | 対象の名前 |
| design_path | str | はい | design.json のパス |
| source_code_path | str | いいえ | ソースコードのパス |
| output_dir | str | はい | 出力先ディレクトリ |

### 実行例 (サブプロセス)

```python
run_skill_script(
    file_path="scripts/main.py",
    args={
        "input_json": "{\"param\": \"value\"}",
        "output_json": "/workspace/src/.workflow_tmp/output.json"
    }
)
```
