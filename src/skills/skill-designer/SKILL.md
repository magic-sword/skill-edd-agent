---
name: skill-designer
description: 設計情報（Pydanticスキーマ等）を動的にロードし、ADK 2.0仕様に準拠したSKILL.mdを生成します。
---

# skill-designer

## 概要

このスキルは、Google ADK 2.0 互換の `design.json` ファイルを自動的に設計・生成することを目的としています。ユーザーが提供する自然言語の要件と、オプションで既存のソースコードを解析し、それに基づいて適切な `design.json` を出力します。具体的な動作は以下の通りです。1. 入力の受け取り: ユーザーから「要件 (requirement)」、「出力ディレクトリ (output_dir)」、およびオプションで「既存のソースコードパス (source_code_path)」を受け取ります。2. パスの正規化と自動検出: `output_dir` や `source_code_path` が相対パスの場合、絶対パスに変換します。`source_code_path` が指定されていない場合、`output_dir` 内の `scripts` ディレクトリから `main.py` または唯一の Python ファイルを自動的に検出し、既存のソースコードとして利用します。3. 既存スキル名の特定: 再設計の際に一貫性を保つため、既存のソースコードパス、既存の `design.json`、または出力ディレクトリ名からスキル名を特定しようと試みます。4. プロンプトの構築: 検出された既存のソースコードとユーザーの要件を組み合わせて、Gemini API に渡すためのプロンプトを構築します。5. Gemini API の呼び出し: 構築されたプロンプトと `SkillDesign` の Pydantic スキーマを `gemini-2.5-flash` モデルに渡し、ADK 2.0 互換の `design.json` 構造を生成させます。6. `design.json` の保存: Gemini API から返された JSON データをパースし、指定された `output_dir` 内に `design.json` として保存します。これにより、開発者は複雑な `design.json` の手動作成から解放され、自然言語でスキルやワークフローの設計を行うことが可能になります。

## トリガー条件

- 新しいスキルを設計して、`design.json` を生成してください。
- この要件に基づいて、`output_dir` にスキルを設計してください。
- 既存のソースコード `path/to/main.py` を使って、`design.json` を更新してください。
- `output_dir` にワークフローの `design.json` を作成して。
- スキル `my-skill` の `design.json` を再設計して。

## AIエージェント向け使用方法

### 1. 実行手順（Instructions）

あなた（エージェント）がこのスキルをトリガーした場合は、以下の手順に従ってください。

1. 必要な入力パラメータ（`target_type`, `name`, `design_path`, `output_dir`など）を決定します。
2. 決定したパラメータを指定して、このスキルを起動してください。
3. 実際の処理（API呼び出しやファイル出力など）は内部スクリプト側で完結するため、あなた自身が内部テンプレートを読み込んで推論したり、成果物を手動で組み立てたりする必要はありません。


### 2. 呼び出し方法

このスキルは、インプロセス（Python関数のロード）およびサブプロセス（`run_skill_script`によるCLI実行）の双方の実行モードをサポートします。

#### インプロセス呼び出し (Python API)
ワークフローや他の親エージェントから直接ロードして呼び出す場合は、以下のインターフェースを使用します。

* **ロード関数名**: `process_message`
* **入力状態 (`tool_context.state`)**:
  * スキルのパラメータが直接状態（キー/値）として設定されます。
* **出力状態 (`tool_context.state`)**:
  * 処理の成否や結果データが直接状態に書き込まれます。

#### サブプロセス呼び出し (CLI)
* **実行ファイル**: `scripts/skill_designer.py`
* **引数 (`args`)**:
  * `input_json`: パラメータ情報を含む JSON 文字列
  * `output_json`: 結果を一時保存するファイルパス

#### 出力形式の要件 (Output Mode)
- **Output Mode: STRUCTURED_JSON**
  特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| target_type | str | はい | 生成対象のタイプ（'skill' または 'workflow'）。 |
| name | str | はい | 生成対象のスキルまたはワークフロー名。 |
| design_path | str | はい | 設計定義ファイルのパス、またはスキルのルートディレクトリ。 |
| output_dir | str | はい | 生成されたSKILL.mdを保存するディレクトリのパス。 |
| source_code_path | str | いいえ | メインロジックのソースコードファイルパス。指定しない場合、自動的に検出を試みます。 |

### 実行例 (サブプロセス)

```python
run_skill_script(
    file_path="scripts/skill_designer.py",
    args={
        "input_json": "{\"param\": \"value\"}",
        "output_json": "/workspace/src/.workflow_tmp/output.json"
    }
)
```
