---
name: skill-spec-writer
description: 設計情報（parameters, dependencies）と実装コードを入力として受け取り、LLMで端的な説明文（Pydantic構造化出力）を生成した上で、多態的クラスを用いて決定論的にMarkdown仕様書（SKILL.md）を構築して指定ディレクトリに保存するドキュメント自動生成スキル。
---

# skill-spec-writer

設計情報（parameters, dependencies）と実装コードを入力として受け取り、LLMで端的な説明文（Pydantic構造化出力）を生成した上で、多態的クラスを用いて決定論的にMarkdown仕様書（SKILL.md）を構築して指定ディレクトリに保存するドキュメント自動生成スキル。

## 設計基準（Pydanticの活用とプロンプト簡素化）

本スキルで LLM (Gemini API) 呼び出しを行う場合は、以下の ADK 設計基準に準拠してください：
1. **Pydantic による構造化出力 (response_schema)**: 出力データの形式を Pydantic モデル（`BaseModel`）で定義し、Gemini API の `response_schema` に設定して構造化出力を得てください。Few-Shot の例は Pydantic `Field` の `examples` パラメータとして定義します。
2. **外部プロンプトファイルの利用**: プロンプト指示そのものは `assets/` ディレクトリ配下にテキストファイル（`prompt.txt` 等）として分離し、実行時に動的にロードして使用してください。プロンプトには出力構造（JSONフォーマット）に関する指示を含めず、簡潔に記述します。

## トリガー条件

- ユーザーがこのスキルの実行を求めた場合。

## スキルの動作

1. `user_message` から入力を受け取ります。
2. 処理を行い、結果を `result_message` に格納します。

## AIエージェント向け使用方法

このスキルは `run_skill_script` ツールを使用して実行します。
`stdout` から結果の JSON を直接取得して読み取ってください。

### 出力形式の要件 (Output Mode)
- **Output Mode: CONVERSATIONAL**
  読み取った結果を踏まえて、ユーザーに対して自然な対話応答メッセージを生成して返却してください。

### パラメータ

- `file_path`: `scripts/spec_writer.py`
- `args`: JSON引数として以下を渡してください。
  - `input_json`: `{"user_message": "入力テキスト"}`
  - `output_json`: 結果を一時保存するファイルパス

### 実行例

```
run_skill_script(
    file_path="scripts/spec_writer.py",
    args={
        "input_json": "{\"user_message\": \"hello world\"}",
        "output_json": "/workspace/src/.workflow_tmp/output.json"
    }
)
```
