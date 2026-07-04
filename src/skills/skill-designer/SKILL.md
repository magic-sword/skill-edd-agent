---
name: skill-designer
description: スキル設計要件に基づいて新しいスキルを設計し、または既存スキルを再設計するツール。
---

# skill-designer

## 概要

このスキルは、Google ADK 2.0 互換の `design.json` を設計・生成するためのツールです。ユーザーが指定する自然言語の機能要件や、既存のスキル実装コードを基に、Generative AI (Gemini) を利用して `design.json` を自動的に作成します。主な機能は以下の通りです。

1.  **要件に基づく設計**: 自然言語で記述されたスキルの機能要件 (`requirement`) を入力として受け取り、それに基づいて `design.json` の内容を生成します。
2.  **既存スキルの再設計**: 既存のスキル実装コードのファイルパス (`source_code_path`) を指定することで、そのコードを解析し、より洗練された `design.json` を再設計・出力できます。`source_code_path` が指定されない場合でも、`output_dir` 内の `scripts` ディレクトリから `main.py` やその他のPythonファイルを自動的に検出し、既存コードとして利用を試みます。
3.  **スキル名の自動特定**: 再設計時には、既存のソースコードパス、既存の `design.json`、または出力ディレクトリ名から、元のスキル名を決定論的に特定し、設計に反映させます。
4.  **出力管理**: 生成された `design.json` は、指定された出力ディレクトリ (`output_dir`) に保存されます。必要に応じてディレクトリが自動的に作成されます。

このスキルは、開発者が手動で `design.json` を作成する手間を省き、効率的なスキル開発を支援することを目的としています。

## トリガー条件

- スキルを設計して
- 新しいスキルを作成して
- 既存のスキルを再設計して
- design.json を生成して
- この要件でスキルを設計して

## AIエージェント向け使用方法

### 1. 実行手順（Instructions）

あなた（エージェント）がこのスキルをトリガーした場合は、以下の手順に従ってください。

1. 必要な入力パラメータ（`requirement`, `output_dir`など）を決定します。
2. 決定したパラメータを指定して、このスキルを起動してください。
3. 実際の処理（API呼び出しやファイル出力など）は内部スクリプト側で完結するため、あなた自身が内部テンプレートを読み込んで推論したり、成果物を手動で組み立てたりする必要はありません。


### 2. 呼び出し方法

このスキルは、インプロセス（Python関数のロード）およびサブプロセス（`run_skill_script`によるCLI実行）の双方の実行モードをサポートします。

#### インプロセス呼び出し (Python API)
ワークフローや他の親エージェントから直接ロードして呼び出す場合は、以下のインターフェースを使用します。

* **ロード関数名**: `process_message`
* **入力状態 (`tool_context.state`)**:
  * `tool_context.state["validated_input"]` に、`Input` スキーマのインスタンス（検証済みオブジェクト）が設定されます。
* **出力状態 (`tool_context.state`)**:
  * 処理結果データが状態に直接書き込まれます。

#### サブプロセス呼び出し (CLI)
* **起動方法**: `python3 -m edd_agent_tools.cli.run --skill_name skill-designer <引数>`
* **引数 (`args`)**:
  * Pydantic スキーマで定義されているパラメータをフラットなオプション引数として直接渡します（例: `--param_name value`）。

#### 出力形式の要件 (Output Mode)
- **Output Mode: STRUCTURED_JSON**
  特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| requirement | str | はい | 設計するスキルの機能要件を記述した自然言語のテキスト。 |
| output_dir | str | はい | 生成されたdesign.jsonを保存するディレクトリのパス。 |
| source_code_path | str | いいえ | 再設計のベースとなる既存のスキル実装コードのファイルパス。指定しない場合、自動的に検出を試みます。 |

### 実行例 (サブプロセス)

```python
run_skill_script(
    file_path="/workspace/edd-agent-tools/src/edd_agent_tools/cli/run.py",
    args={
        "--skill_name": "skill-designer",
        # Pydantic schema に定義された引数を指定します:
        # "--param_name": "value"
    }
)
```
