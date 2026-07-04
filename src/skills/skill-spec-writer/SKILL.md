---
name: skill-spec-writer
description: 設計パラメータとソースコードからスキル仕様書を自動生成するツール。
---

# skill-spec-writer

## 概要

このスキルは、Google ADK 2.0 互換のスキル仕様書（SKILL.md）を自動生成するためのツールです。入力として、対象の種類（スキルまたはワークフロー）、対象の名前、design.jsonのパス、オプションでソースコードのパス、および出力先ディレクトリを受け取ります。これらの情報に基づいて、機械（LLM）向けの簡潔な要約と、人間（開発者）向けの機能・動作説明を含む詳細な仕様書を生成します。これにより、開発者は手動でのドキュメント作成の手間を省き、一貫性のある高品質な仕様書を効率的に作成できます。`process_message`関数が主要なロジックを担い、コマンドラインからの実行をサポートします。

## トリガー条件

- スキル仕様書を作成してください
- このスキルの仕様書を生成して
- 指定された設計パラメータとコードからSKILL.mdを作成
- skill-spec-writer を使ってドキュメントを生成して
- 設計情報に基づいてスキル仕様書を書き出して

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

- **Output Mode: STRUCTURED_JSON**
  スキル仕様書の生成結果をJSON形式で返します。成功時には生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。これにより、他のシステムやワークフローが生成結果をプログラム的に処理しやすくなります。

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
