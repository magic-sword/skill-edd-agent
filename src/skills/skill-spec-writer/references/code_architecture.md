# skill-spec-writer コードアーキテクチャ (Code Architecture)

このドキュメントは、`skill-spec-writer` の **Python ソースコード（システム実装）**の設計思想およびアーキテクチャ原則をまとめた実装ガイドです。

AI（SkillDeveloperAgent）がこのスキルのソースコードを改修・拡張する際は、本ドキュメントに記述された設計構造を厳格に遵守してください。

---

## 1. Template Method パターンによる実装の DRY 化

仕様書生成ロジックの重複コードを徹底的に排除し、システムの堅牢性を保つため、プログラムの構造には **Template Method パターン**を採用しています。

* **親クラス (`BaseSpecWriter`) の責務**:
  * Gemini API の呼び出しフロー（`generate` メソッド）や、Pydantic型フォーマット関数（`_format_parameter_type`）などの基本ユーティリティは、すべて [base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/base.py) に一元化して記述します。
* **中間共通クラス (`BaseSkillSpecWriter`) の責務**:
  * 複数公開関数（`functions` リスト）を持つ「スキル型モジュール」の仕様書合成（`render_markdown`）は、[skill_base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/skill_base.py) に定義し、関数ごとのカプセル化（詳細、入力、警告ガイド、出力仕様の統合）を行います。
* **具象クラス (`AgentSpecWriter` / `ToolSpecWriter` / `WorkflowSpecWriter`) の責務**:
  * 各具象クラスは、固有の実行手順書アセットをロードして展開する `_build_execution_instructions` メソッドのみを記述（オーバーライド）します。これ以外の共通処理を具象クラス側に記述することは禁止します。
  * `WorkflowSpecWriter` は、ワークフロー専用の [workflow_spec.md.template](file:///workspace/src/skills/skill-spec-writer/assets/workflow_spec.md.template) テンプレートを独自にロードして合成します。

---

## 2. Pydantic モデル継承による記述抽出と LLM の制御

Gemini から非決定論的な説明テキストを構造化JSONとして抽出する際、出力される説明トーン（LLMの思考）を制御するため、Pydanticの継承構造を利用します。

* **親スキーマ (`BaseSkillTextParts`)**:
  * 共通する説明フィールド（`purpose`, `features`, `trigger_conditions`）は、親モデルである `BaseSkillTextParts`（[skill_base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/skill_base.py)）に定義し、不要な重複スキーマ定義を根絶します。
* **具象スキーマによるトーンの上書き**:
  * LLMに対するフィールドの `Field(description="...")` 指示はプロンプトそのものとして機能します。そのため、実行タイプ（`agent`/`tool`）で大きく書き分ける必要がある `workflow_steps` フィールドのみ、具象クラス（`AgentSkillTextParts` / `ToolSkillTextParts`）のローカルで個別に定義（オーバーライド）し、記述の書き分け品質をコントロールします。

---

## 3. メタデータの関数カプセル化と境界条件の解決

`design.json` に記述された宣言的メタデータ（ハルシネーション防衛用のハーネス）を、仕様書内の該当する公開関数の配下にカプセル化してマージするロジックを記述します。

* **プロンプトガイドラインの関数紐付け**:
  * `is_prompt_parameter` なフィールドを検知した場合は、その `prompt_instructions` や `prompt_constraints` を抽出し、仕様書内の該当する関数の入力パラメータテーブルの直下に警告枠として自動結合します。
* **境界条件（全引数オプション）における安全なパラメータフォールバック**:
  * 複数公開関数において「ある関数の引数がすべてオプション（必須引数がない）」という状況においても、他の関数の引数名が混入して `execution_instructions_tool.txt` に展開されるのを防ぐため、[skill_base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/skill_base.py) 側でフォールバック引数を「その関数」のパラメータに閉じて解決してから具象クラスの `_build_execution_instructions` を呼び出す防衛策を実装しています。
* **仕様概要の決定論的切り替え**:
  * `render_markdown` において、`self.design_data.summary` がロードされている場合は、LLMの推論処理をバイパスし、その内容を優先的かつ決定論的に採用して仕様書の概要（Overview）に出力します。
