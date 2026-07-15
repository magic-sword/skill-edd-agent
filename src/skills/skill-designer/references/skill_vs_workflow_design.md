# スキル (SKILL) とワークフロー (WORKFLOW) の設計境界およびスキーマアーキテクチャ

本ドキュメントでは、ADK 2.0 スキーマ（`design.json`）のデータクラス定義における、単体スキル（`ModuleType.SKILL`）とワークフローエージェント（`ModuleType.WORKFLOW`）の設計思想およびスキーマの切り分けに関する基準を解説します。

---

## 1. 概念定義と関心の分離

ADK 2.0 におけるモジュールは、その本質的な役割に応じて明確に 2 つに分類されます。

### ① スキル (SKILL)
*   **本質**: 共通のデータドメインやロジックを集約した最小限の機能モジュール（マイクロサービス）。
*   **特徴**:
    *   特定の役割（ドメイン）に凝集した1つ以上の関連する公開関数（APIエンドポイント）を `scripts/handler.py` に定義し、`scripts/__init__.py` から同時にエクスポートできます。
    *   実行ロジック（`executor.py`）が Python スクリプトなどで自己完結しており、内部の細かい手順はプログラム的に処理されます。
    *   スキーマレベルでは「ステップ（順序関係）」の概念を持たず、**「公開されたAPIエンドポイント（関数リスト）」** を提供するサービスノードとして機能します。

### ② ワークフロー (WORKFLOW)
*   **本質**: 複数の異なるスキル、カスタム Python 処理、自律エージェントを「繋ぎ合わせて一連の業務プロセスを構成する」パイプライン。
*   **特徴**:
    *   ノード間をデータが流れるように順序づけられた **「多数のステップ（有向グラフ）」** を持ちます。

---

## 2. スキーマレベルでの切り分けとバリデーション

スキーマクラス（`SkillDesign`）において、`steps`（ステップリスト）フィールドを `ModuleType.WORKFLOW` 専用の構造とし、通常の `SKILL` では禁止（バリデーションエラー）する設計を採用しています。

### なぜ SKILL のときに steps を禁止するのか？

1.  **関心の分離の徹底**:
    もし単体のスキル（SKILL）の中にスキーマとして「多数のステップ」を許容してしまうと、「スキル」と「ワークフロー」の境界線が曖昧になります。あるスキルの中に別のスキルをネストさせてステップ実行するようなネスト構造を許すと、パイプラインの管理が極端に複雑化します。
2.  **決定論的コード生成の担保**:
    コードジェネレータ（`code_generator.py`）は、設計情報（`design.json`）の `module_type` と構造を読み取って自動生成を行います。
    *   `SKILL` ➔ `executor.py`（単一のビジネスロジック実行ファイル）を出力。
    *   `WORKFLOW` ➔ `workflow.py`（各ノードを関数接続する DAG 定義ファイル）を出力。
    境界線がスキーマレベルで厳格に定義されていることで、ジェネレータが迷うことなく正しいボイラープレートを決定論的に出力できます。

*※スキル内で「分析 ➔ 生成 ➔ 保存」といった複数の手順を行いたい場合は、スキーマ上のステップではなく、生成された `executor.py` の内部 Python コードとして実装するか、それぞれを別スキルに切り出して `WORKFLOW` で接続するのが正しいアプローチです。*

---

## 3. 具体的なデータモデル構造 (edd-agent-tools)

スキーマ定義（Pydantic）では、この設計思想を以下の多態的（Polymorphic）モデルで定義しています。

### ステップ構造モデル
```python
class StepType(StrEnum):
    SKILL = "skill"       # 既存スキルのロードと呼び出し
    FUNCTION = "function"  # 決定論的な Python カスタム処理関数の実行
    AGENT = "agent"       # LLM推論による自律エージェントへの処理委託

class Step(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別")
    target: str | None = Field(None, description="既存のスキル名 (type='skill' 時に必須)")
    description: str | None = Field(None, description="処理要件の説明 (type='function'/'agent' 時に必須)")
    instruction: str | None = Field(None, description="システムプロンプト指示 (type='agent' 時に任意)")
    tools: list[str] | None = Field(None, description="使用可能ツール (type='agent' 時に任意)")
    inputs: dict[str, str] | None = Field(None, description="引数マッピング辞書")
```

### 設計定義モデル（Union 分離）
```python
class FunctionDefinition(BaseModel):
    """複数公開関数を設計する場合の、個別関数の定義情報を表すモデル。"""
    name: str = Field(..., description="公開関数名。小文字のスネークケース")
    description: str = Field(..., description="関数の役割や目的の説明")
    parameters: list[Parameter] = Field(..., description="関数の入力パラメータリスト")
    response_parameters: list[Parameter] | None = Field(None, description="関数の構造化出力パラメータ定義（STRUCTURED_JSON時に使用されます）")

class SkillDesign(BaseModel):
    """単一スキルの設計定義を表す Pydantic モデル。"""
    rationale: str = Field(..., description="設計の思考プロセス。")
    name: str = Field(..., description="スキルの名前。小文字のハイフン区切り")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="スキルの仕様概要")
    module_type: Literal[ModuleType.SKILL] = Field(ModuleType.SKILL, description="モジュールの役割分類。単一スキルは必ず 'skill'")
    execution_type: Literal["tool", "agent"] = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推論)")
    output_mode: OutputMode = Field(..., description="出力形式（VALUE_ONLY, CONVERSATIONAL, STRUCTURED_JSON）")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")
    constraints: list[str] = Field([], description="モデルバリデータ等から抽出された制約条件のリスト")
    functions: list[FunctionDefinition] = Field(..., description="スキルパッケージが提供する公開関数の定義リスト。1つ以上の関数定義を含める必要があります")

class WorkflowDesign(BaseModel):
    """複数モジュールを連結するワークフローの設計仕様定義。"""
    rationale: str = Field(..., description="設計の思考プロセス。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="ワークフローの仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの役割分類。ワークフローは必ず 'workflow'")
    parameters: list[Parameter] = Field(..., description="ワークフロー全体が外部から受け取るパラメータのリスト")
    dependencies: list[str] = Field([], description="依存するターゲットスキル名のリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    response_parameters: list[Parameter] | None = Field(None, description="全体の出力JSONの構造定義")
    steps: list[Step] = Field(..., description="ワークフローを構成するステップの定義リスト（有向グラフ）")

# Discriminated Union によるロードの多態性
ModuleDesign = Annotated[
    Union[SkillDesign, WorkflowDesign],
    Field(discriminator="module_type")
]
```

---

## 4. 意味論的な設計判断と Chain-of-Thought (rationale) の役割

設計の自動化エージェント（`skill-designer`）が、与えられた要件の難易度に基づいて「スキル」と「ワークフロー」を正しく切り分けるために、スキーマの最上部に **`rationale`（思考プロセス）** フィールドを統合しています。

### Chain-of-Thought (CoT) の強制
1. **生成順序の重要性**:
   Pydantic モデルで `rationale` を最上部に定義することで、Gemini API は JSON を出力する最初のステップでこのフィールドを生成します。
2. **難易度と手順の自己分析**:
   LLM は `module_type`（`skill` か `workflow` か）を決定する前に、与えられた要件の難易度や必要な手順を `rationale` 内で詳細に分析します。
   * 「この要件は1つの機能で完結するか？」
   * 「既存のスキルを組み合わせたり、データ処理関数や LLM 判定ノードをつなぐ必要があるか？」
   といった思考をテキストで展開させた上で、残りの `module_type` や `steps` などの具体的なパラメータ値を決定論的に決定します。これにより、判断のハルシネーション（誤判定）が劇的に低下します。
3. **推論プロセスの静的保存**:
   生成された `design.json` には、AI がどのような論理的思考でその構成に至ったかの推論トレースが `rationale` フィールドとして静的に残ります。これは、人間が設計レビューやデバッグを行う際にも極めて重要なドキュメント情報になります。

---

## 5. LLM の過剰ワークフロー化（Over-Workflowing）問題とハーネス設計

LLM（Gemini API）に設計を指示すると、内部手続き（パス解決、ファイルの保存、バリデーションなど）をすべて ADK の物理的な「ステップ」に過剰分割し、なんでもワークフロー（`workflow`）に仕立て上げてしまう傾向（過剰ワークフロー化）があります。これに対し、プロジェクトでは「Pydanticスキーマ」と「クレンジング処理（防錆境界）」の二段構えで構造的な制約（ハーネス）を設けています。

### ① Pydantic スキーマ（骨組みモデル）による構造的制約
粗設計（L1）のデータ定義において、当初はワークフローモデル（`WorkflowSkeletonDesign`）しか許容されていなかったため、LLMは強制的に `workflow` を選択せざるを得ませんでした。

これを、アトミックなスキル設計用の項目も包含するフラットな単一の [SkeletonDesign](file:///d:/kaggle/antigravity/skill-edd-agent/src/skills/skill-designer/scripts/skeleton_models.py) モデルに統合しました。
*   `steps` をオプショナル（デフォルト空リスト）にする。
*   `module_type` として `"skill"` も選択できるように `description` を追加する。
*   複雑な `Union` 分岐を避けることで、Gemini APIの制約上限（too many states）エラーを回避しつつ、LLMに対して型定義レベルで「アトミックなスキル」という正しい選択肢を提示しています。

### ② 防錆境界としての決定論的クレンジング（Anticorruption Layer）
LLMのハルシネーションに対する「お節介な自動補正」をスキーマ定義自体に `@model_validator` などとして埋め込むことは避けています。

理由は以下の通りです：
*   **関心の分離**: スキーマはデータの本質的な整合性ルール（不変条件）の検証に特化させ、LLM固有の揺らぎに対する補正処理（サニタイズ）は外部の [cleanser.py](file:///d:/kaggle/antigravity/skill-edd-agent/src/skills/skill-designer/scripts/cleanser.py) に切り分ける。
*   **循環インポートの回避**: スキーマは他のモジュールから広くインポートされるため、そこに状態や外部依存をロードするロジックを混ぜると循環参照の原因になります。

[cleanser.py](file:///d:/kaggle/antigravity/skill-edd-agent/src/skills/skill-designer/scripts/cleanser.py) は防錆境界として働き、LLMが「外部のスキル（`type: skill`）を1つも呼び出していない擬似ワークフロー」を出力した場合は、決定論的に `module_type: skill` へ強制的に引き戻し、不要な `steps` を除去した上でアトミックなスキル用必須フィールド（`execution_type`, `output_mode`, `functions`）を補完します。これにより、過剰にファイルが自動生成されてコードベースが汚染されるのを未然に防いでいます。
