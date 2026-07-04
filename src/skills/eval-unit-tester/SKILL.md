---
name: eval-unit-tester
description: 指定されたスキルに対して評価用の単体テストスイート（*.evalset.json）を自動生成します。
---

# eval-unit-tester

## 概要

このスキルは、Google ADK 2.0 互換の評価用単体テストスイート（`.evalset.json`）を自動生成するツールです。指定されたスキル名（`skill_name`）を引数として受け取り、そのスキルに対するテストケースを生成します。AIエージェント（LLM）が直接推論するのではなく、引数を受け取って Python コードが処理を完結させる決定論的なスクリプト処理として機能します。

主な機能と内部処理は以下の通りです。
- **対象スキルの解析**: 指定されたスキル名に基づき、そのスキルの `SKILL.md` ファイルを読み込み、スキルの概要、引数、および `Output Mode`（`VALUE_ONLY`、`CONVERSATIONAL`、`STRUCTURED_JSON`）を解析します。
- **動的なスキーマロード**: 対象スキルの `handler.py` から `Input` Pydantic スキーマを動的にロードし、テストケース生成時の `input_parameters` の構造を正確に把握します。
- **プロンプトの動的生成**: 解析したスキル情報（`SKILL.md`の内容、`Input`スキーマ、`Output Mode`に応じた指示）を基に、Gemini API に渡すプロンプトを動的に構築します。特に `Output Mode` に応じて、`user_instruction` と `expected_output` の形式に関する具体的な制約をプロンプトに含めます。
  - `VALUE_ONLY`: ユーザー入力に「〜〜の結果のみを出力してください」という制約を含め、期待応答は結果そのものとします。
  - `CONVERSATIONAL`: ユーザー入力は自然なメッセージとし、期待応答は自然な対話応答とします。
  - `STRUCTURED_JSON`: 期待応答は余計な解説を一切排した生の JSON 文字列のみとします。
- **Gemini API によるテストケース生成**: 構築したプロンプトと、動的に生成されたレスポンススキーマ（`TestParameterSet`または`DynamicTestParameterSet`）を使用して Gemini API を呼び出し、複数のテストケース（`user_instruction`、`input_parameters`、`expected_output`）を生成します。
- **ADK 2.0 形式での保存**: 生成されたテストケースは、Google ADK 2.0 の評価セット形式（`.evalset.json`）に変換されます。このファイルには、ユーザーの指示、ツール呼び出しの引数、期待される最終応答、および中間データ（ツール呼び出しと応答）が含まれます。
- **設定ファイルの生成**: 生成された `.evalset.json` に対応する評価設定ファイル（`.evalset.config.json`）も同時に生成され、テストの実行に必要な情報（精度閾値など）が定義されます。

これにより、開発者は新しいスキルを実装した際に、迅速かつ自動的に評価用の単体テスト環境を構築できます。

## トリガー条件

- 「[スキル名]」の単体テストを生成してください
- 「[スキル名]」の評価用テストスイートを作成して
- 「[スキル名]」のテストケースを自動生成してほしい
- 「[スキル名]」の評価セットを作って
- 「[スキル名]」のテストファイルを生成して

## AIエージェント向け使用方法

### 1. 実行手順（Instructions）

あなた（エージェント）がこのスキルをトリガーした場合は、以下の手順に従ってください。

1. 必要な入力パラメータ（`skill_name`など）を決定します。
2. 決定したパラメータを指定して、このスキルを起動してください。
3. 実際の処理（API呼び出しやファイル出力など）は内部スクリプト側で完結するため、あなた自身が内部テンプレートを読み込んで推論したり、成果物を手動で組み立てたりする必要はありません。


### 2. 呼び出し方法

このスキルは、インプロセス（Python関数のロード）による親エージェントとのシームレスな連携、およびCLIを用いた手動での検証実行をサポートします。

#### インプロセス呼び出し (Python API)
他の親エージェントから直接ロードして呼び出す場合は、以下のインターフェースを使用します。

* **ロード関数名**: `process_message`
* **入力状態 (`tool_context.state`)**:
  * `tool_context.state["validated_input"]` に、`Input` スキーマのインスタンス（検証済みオブジェクト）が設定されます。
* **出力状態 (`tool_context.state`)**:
  * 処理結果データが状態に直接書き込まれます。

#### サブプロセス呼び出し (CLI)
* **起動方法**: `python3 -m edd_agent_tools.cli.run --skill_name eval-unit-tester <引数>`
* **引数 (`args`)**:
  * Pydantic スキーマで定義されているパラメータをフラットなオプション引数として直接渡します（例: `--param_name value`）。

#### 出力形式の要件 (Output Mode)
- **Output Mode: VALUE_ONLY**
  出力は単純なプレーンテキストの値のみとなります。

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill_name | str | はい | テストケースを生成する対象のスキル名 |



### 実行例

#### 1. インプロセス呼び出し (推奨)
親エージェントが本スキルを動的ロードしてプログラムから起動する推奨コード例です。

```python
# 1. スキルのロード
skill = load_skill("eval-unit-tester")

# 2. 状態に引数を設定して実行
# ※ 引数は validated_input 経由で process_message に渡されます
# tool_context.state["validated_input"] = Input(...)
skill.process_message(tool_context)
```

#### 2. サブプロセス呼び出し (手動テスト用 CLI)
開発環境などで本スキルを手動で動作確認する際の起動コマンド例です。

```bash
python3 -m edd_agent_tools.cli.run --skill_name eval-unit-tester --name "target-skill-name"
```
