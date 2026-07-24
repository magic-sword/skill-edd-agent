# skill-spec-writer アーキテクチャ設計書

本ドキュメントは、仕様書自動生成スキルである `skill-spec-writer` の全体構造、採用しているデザインパターン、およびコードベースの拡張性を維持するための設計思想についてまとめたものです。

---

## 1. 全体アーキテクチャ概要

`skill-spec-writer` は、対象となるスキルの設計データ（`design.json`）とソースコードを読み込み、Gemini API を用いてセマンティックな情報を抽出しつつ、決定論的かつ一貫した Markdown 仕様書（`SKILL.md`）を出力するスキルです。

システムは以下の主要コンポーネントで構成されています。

```mermaid
classDiagram
    class SpecWriterFactory {
        +create(design_data, source_code_dir, prompt) BaseSpecWriter
    }
    class BaseSpecWriter {
        <<Abstract>>
        +design_data Union[SkillDesign, WorkflowDesign]
        +source_code_dir str
        +generate(output_dir) str
        #_call_gemini_api(contents, schema) model
        +get_pydantic_schema()*
        +build_prompt(prompt_tmpl)* str
        +render_markdown(text_parts)* str
        #_format_parameter_type(param) str
        #_format_parameter_description(param) str
    }
    class BaseSkillSpecWriter {
        <<Abstract>>
        +render_markdown(text_parts) str
        #_build_execution_instructions(required_params)* str
    }
    class ToolSpecWriter {
        +get_pydantic_schema() ToolSkillTextParts
        +build_prompt(prompt_tmpl) str
        #_build_execution_instructions(required_params) str
    }
    class AgentSpecWriter {
        +get_pydantic_schema() AgentSkillTextParts
        +build_prompt(prompt_tmpl) str
        #_build_execution_instructions(required_params) str
    }
    class WorkflowSpecWriter {
        +get_pydantic_schema() WorkflowTextParts
        +build_prompt(prompt_tmpl) str
        +render_markdown(text_parts) str
        #_build_execution_instructions(required_params) str
    }

    SpecWriterFactory ..> BaseSpecWriter : Instantiates
    BaseSpecWriter <|-- BaseSkillSpecWriter : Inherits
    BaseSpecWriter <|-- WorkflowSpecWriter : Inherits
    BaseSkillSpecWriter <|-- ToolSpecWriter : Inherits
    BaseSkillSpecWriter <|-- AgentSpecWriter : Inherits
```

---

## 2. 適用されているデザインパターン

堅牢性と拡張性を確保するため、オブジェクト指向設計の古典的なデザインパターンを採用しています。

### ① Factory Pattern（ファクトリ・パターン）
* **該当クラス**: `SpecWriterFactory` ([factory.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/factory.py))
* **採用理由**:
  モジュールの分類（`skill` または `workflow`）および実行形式（`"tool"` または `"agent"`) によって、仕様書の生成プロセスやプロンプト指示、レンダリング方法が大きく異なります。
  呼び出し側（`spec_generator.py`）が個別の具象ライタークラスの存在やインスタンス化ロジックを直接知る必要をなくし、オブジェクトの作成責務を完全にカプセル化しています。
* **なぜタイプを分けるのか（ADK/Playbooksの思想背景）**:
  ADKおよびGoogle Cloud Conversational Agents（Playbooks）のアーキテクチャ設計では、エージェントが利用するツール（スキル）の責務について、**「決定論的（確定・安定）な処理」**と**「非決定論的（自律思考・推論）な処理」**を技術的・概念的に厳格に分離しています。
  * **`tool` タイプ (`PythonFunction` / `ClientFunction` 等の具象)**:
    * **目的**: ファイルI/OやAPIリクエストなどの「決定論的なシステム操作」を、安全かつ確実に実行させるための概念です。エージェント（LLM）自身に操作手順を考えさせるのではなく、プログラムコードで機械的に完結させるため、厳密な引数定義と手順書の自動出力が必要になります。
  * **`agent` タイプ (`AgentTool` / `Sub-Agent` の具象)**:
    * **目的**: 複雑な課題（設計、コーディングなど）を、別の「LLMによる自律思考を持ったエージェント（Playbook）」へ委譲するための概念です。エージェントの中に別のエージェントをネストさせるため、引数の受け渡しだけでなく「思考のステップや方針（Instructions）」にフォーカスした仕様定義が必要です。
  * **仕様書を読み込むAIエージェントのトークン消費と注意力の最適化**:
    AIエージェントが利用可能なスキル群から適切なものを選択・実行する際、各スキルの仕様書（`SKILL.md`）をシステムプロンプト（コンテキスト）としてロードします。この際の**AIのトークン消費量の最小化**と、**適切な役割認識（アテンションの制御）**がタイプ分割の核心的な理由です。
    * **`tool` スキルを読み込む時**: AIは「関数のインターフェース（正しい引数と返り値の型）」だけを正確に理解できれば十分です。もしここに無駄な思考指示やプロンプトが含まれていると、AIは**無関係な情報にコンテキストトークンを浪費し、アテンション（注意力）が散漫になってパラメータ設定エラーを引き起こします。** 本スキルでは、冗長な共通指示を排除し、トークンのスリム化を図る構成になっています。
    * **`agent` スキルを読み込む時**: AIは「そのサブエージェントがどのような思考指示（Instructions）に沿って自律的に推論するか」を理解する必要があります。仕様書に思考プロセスが明記されていることで、AIはこれが「機械的なツール」ではなく「仕事を委譲すべき自律的なエージェント」であると正しく認識し、適切なコンテキストを渡して委譲できるようになります。
  * **リファレンスリンク**:
    * ADK 公式スキル設計ガイド: [Skills for ADK agents](https://adk.dev/skills/index.md)
    * ADK 公式エージェント設計ガイド: [Simple agents](https://adk.dev/agents/llm-agents/index.md)
    * Google Cloud Playbooks Tools 概念詳細: [playbooks_tools_concept.md](file:///workspace/src/skills/skill-spec-writer/references/playbooks_tools_concept.md)

### ② Template Method Pattern（テンプレートメソッド・パターン）
* **該当クラス**: `BaseSpecWriter` ([base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/base.py))
* **採用理由**:
  「共通アセットのロード ➔ プロンプトの組み立て ➔ Gemini APIの呼び出しとJSONパース ➔ ディレクトリ作成とファイル書き込み」という**仕様書生成のライフサイクル（アルゴリズムの骨格）は、すべての実行タイプで共通**です。
  `BaseSpecWriter.generate()` メソッドでこの不変の共通アルゴリズムを一元定義し、バリエーションが生じる「スキーマの返却（`get_pydantic_schema`）」「プロンプト構築（`build_prompt`）」「Markdownレンダリング（`render_markdown`）」のみを具象クラスでオーバーライド（実装）させることで、コードの重複（DRY）を排除しています。

---

## 3. 複数関数公開への適応設計（マイクロサービス型カプセル化）

1つのスキルパッケージが複数の公開関数（APIエンドポイント）をエクスポートするリファクタリング仕様に対応するため、[skill_base.py](file:///workspace/src/skills/skill-spec-writer/scripts/writer/skill_base.py)（`BaseSkillSpecWriter`）において、関数単位での情報カプセル化（概要・引数・戻り値・プロンプト警告枠の統合）をレンダリング時に決定論的に行う設計を導入しました。

これにより、ドキュメント全体での情報分散を防ぎ、LLMおよび人間が読み取った際の誤解の発生を根本から防いでいます。

---

## 4. データ抽出とバリデーション

Gemini APIの呼び出しにおいて、Pydantic v2モデルを直接スキーマとして引き渡し、かつ `json.loads` でパースした後に `model_validate` で型検証を行っています。
これにより、LLMの非決定論的な応答に対して、ランタイム時の強固な型安全性が保証されています。
