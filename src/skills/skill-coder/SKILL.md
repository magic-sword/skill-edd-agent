---
name: skill-coder
description: 設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コード(scripts/handler.py, scripts/logic.py等)を自動生成・更新するスキル
---

# skill-coder

設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コード(scripts/handler.py, scripts/logic.py等)を自動生成・更新するスキル

## 設計基準（Pydanticの活用とプロンプト簡素化）

本スキルで LLM (Gemini API) 呼び出しを行う場合は、以下の ADK 設計基準に準拠してください：
1. **Pydantic による構造化出力 (response_schema)**: 出力データの形式を Pydantic モデル（`BaseModel`）で定義し、Gemini API の `response_schema` に設定して構造化出力を得てください。Few-Shot の例は Pydantic `Field` の `examples` パラメータとして定義します。
2. **外部プロンプトファイルの利用**: プロンプト指示そのものは `assets/` ディレクトリ配下にテキストファイル（`prompt.txt` 等）として分離し、実行時に動的にロードして使用してください。プロンプトには出力構造（JSONフォーマット）に関する指示を含めず、簡潔に記述します。

## トリガー条件

- ユーザーがこのスキルの実行を求めた場合。

## AIエージェント向け使用方法

### 1. 実行手順（Instructions）

あなた（エージェント）がこのスキルをトリガーした場合は、以下の手順に従ってください。

1. 必要な入力パラメータを決定します。
2. 決定したパラメータを指定して、このスキルを起動してください。
3. 実際の処理（API呼び出しやファイル出力など）は内部スクリプト側で完結するため、あなた自身が内部テンプレートを読み込んで推論したり、成果物を手動で組み立てたりする必要はありません。

### 2. 呼び出し方法

このスキルは、インプロセス（Python関数のロード）およびサブプロセス（CLI実行）の双方の実行モードをサポートします。

#### インプロセス呼び出し (Python API)
* **ロード関数名**: `process_message`
* **入力状態 (`tool_context.state`)**:
  * スキルのパラメータが直接状態（キー/値）として設定されます。
* **出力状態 (`tool_context.state`)**:
  * 処理の成否や結果データが直接状態に書き込まれます。

#### 出力形式の要件 (Output Mode)

- **Output Mode: STRUCTURED_JSON**
  得られた出力を指定された JSON スキーマに準拠した JSON 構造のみで返却します。
