# スキル (SKILL) とワークフロー (WORKFLOW) の設計境界およびスキーマアーキテクチャ

本ドキュメントでは、ADK 2.0 スキーマ（`design.json`）のデータクラス定義における、単体スキル（`ModuleType.SKILL`）とワークフローエージェント（`ModuleType.WORKFLOW`）の設計思想およびスキーマの切り分けに関する基準を解説します。

---

## 1. 概念定義と関心の分離

ADK 2.0 におけるモジュールは、その本質的な役割に応じて明確に 2 つに分類されます。

### ① スキル (SKILL)
*   **本質**: これ以上分割できない最小限の機能単位（アトミックな関数）。
*   **特徴**:
    *   実行ロジック（`executor.py`）が Python スクリプトなどで自己完結しており、内部の細かい手順はプログラム的に処理されます。
    *   スキーマレベルでは「ステップ（順序関係）」の概念を持たず、**「1つの実行処理ノード」** として機能します。

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

スキーマ定義（Pydantic）では、この設計思想を以下のバリデーションルールで強制しています。

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
```

### 設計定義モデルの制約
```python
class SkillDesign(BaseModel):
    name: str
    module_type: ModuleType  # SKILL または WORKFLOW
    steps: list[Step] | None = Field(None, description="ワークフローを構成するステップの定義リスト")

    @model_validator(mode="after")
    def validate_workflow_steps(self) -> "SkillDesign":
        # workflow型以外のときに steps が定義されていればエラーを投げる
        if self.module_type != ModuleType.WORKFLOW:
            if self.steps:
                raise ValueError("steps can only be defined when module_type is 'workflow'")
        return self
```
