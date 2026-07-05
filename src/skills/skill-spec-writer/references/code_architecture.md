# skill-spec-writer コードアーキテクチャ (Code Architecture)

このドキュメントは、`skill-spec-writer` の **Python ソースコード（システム実装）**の設計思想およびアーキテクチャ原則をまとめた実装ガイドです。

AI（SkillDeveloperAgent）がこのスキルのソースコードを改修・拡張する際は、本ドキュメントに記述された設計構造を厳格に遵守してください。

---

## 1. Template Method パターンによる実装の DRY 化

仕様書生成ロジックの重複コードを徹底的に排除し、システムの堅牢性を保つため、プログラムの構造には **Template Method パターン**を採用しています。

* **親クラス (`BaseSpecWriter`) の責務**:
  * Gemini API の呼び出しフロー（`generate` メソッド）や、パラメータ情報・出力モードに基づいた Markdown への決定論的レンダリングロジック（`render_markdown` メソッド）は、すべて [base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/base.py) に一元化して記述します。
* **具象クラス (`AgentSpecWriter` / `ToolSpecWriter`) の責務**:
  * 各具象クラスは、固有の実行手順書アセットをロードして展開する `_build_execution_instructions` メソッドのみを記述（オーバーライド）します。これ以外の共通処理を具象クラス側に記述することは禁止します。

---

## 2. Pydantic モデル継承による記述抽出と LLM の制御

Gemini から非決定論的な説明テキストを構造化JSONとして抽出する際、出力される説明トーン（LLMの思考）を制御するため、Pydanticの継承構造を利用します。

* **親スキーマ (`BaseSkillTextParts`)**:
  * 共通する説明フィールド（`purpose`, `features`, `trigger_conditions`）は、親モデルである `BaseSkillTextParts`（[base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/base.py)）に定義し、不要な重複スキーマ定義を根絶します。
* **具象スキーマによるトーンの上書き**:
  * LLMに対するフィールドの `Field(description="...")` 指示はプロンプトそのものとして機能します。そのため、実行タイプ（`agent`/`tool`）で大きく書き分ける必要がある `workflow_steps` フィールドのみ、具象クラス（`AgentSkillTextParts` / `ToolSkillTextParts`）のローカルで個別に定義（オーバーライド）し、記述の書き分け品質をコントロールします。

---

## 3. メタデータ（`PromptField` / `summary`）のロードと結合ロジック

`design.json` に記述された宣言的メタデータ（ハルシネーション防衛用のハーネス）をプログラム内でロードし、ドキュメントにマージする決定論的処理を記述します。

* **プロンプトガイドラインの動的検知**:
  * `self.design_data.parameters` をループ処理し、`is_prompt_parameter` なフィールドを検知した場合は、その `prompt_instructions` や `prompt_constraints` を抽出し、実行手順書の末尾に自動結合する合成ロジックを実装します。
* **仕様概要の決定論的切り替え**:
  * `render_markdown` において、`self.design_data.summary` がロードされている場合は、LLMの推論処理をバイパスし、その内容を優先的かつ決定論的に採用して仕様書の概要（Overview）に出力します。
