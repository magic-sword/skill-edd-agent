# Agent Skill 設計思想 (Design Philosophy)

本プロジェクトにおける Google ADK 2.0 スキル（Agent Skill）の設計思想とベストプラクティスをここに記録します。

---

## 1. コア思想

### ① エージェントに対するスキルのカプセル化 (Encapsulation)
* スキルは「モジュール化されたカプセル（ブラックボックス）」であるべきです。
* 親エージェントや他のスキルからは、パラメータを渡せば自動的に結果が返ってくる**「抽象化されたツール（関数）」**として見せます。
* エージェントに対し、スキル内部の構成ファイル（`assets/` のプロンプトテンプレートなど）やローレベルなサブプロセスの仕組みを直接意識させてはなりません。

### ② コードを唯一の真実にする (Single Source of Truth)
* パラメータの定義や仕様（スキーマ）を、設定ファイル（`design.json`）と実装コード（Python）の双方に手動で定義すると、必ず整合性が崩れます。
* **Pythonコード（Pydanticモデル）を唯一の真実**とし、仕様書（`SKILL.md`）の引数テーブルやCLIの引数パーサーはすべてコードから自動構築します。

---

## 2. フォルダ構造 of スキル (Convention)

各スキルのフォルダは以下の規約に従って最小限の構造で記述します。

```
src/skills/{skill-name}/
  SKILL.md       # エージェント向け仕様書。handler.py から自動生成される。
  assets/        # (任意) プロンプトテンプレートなどのL3リソース。
  scripts/
    __init__.py  # フォルダをPythonパッケージとして扱うために維持する。
    handler.py   # スキルのインターフェース（メタデータ、Pydanticスキーマ、および窓口）。
    {logic}.py   # 実際の複雑な処理を実行するビジネスロジックファイル。
```

* **`design.json` や `scripts/main.py` などのボイラープレートは一切不要**です。
* スキルのライフサイクルにおいて、`design.json` は「スキル自動生成時の中間メタデータ」に過ぎず、スキル稼働時には残りません。

---

## 3. 探索パス解決規則と論理配置 (Target Entry)

本パッケージは、多様なプロジェクトのフォルダ構成をサポートするために、`skills.json` 内で複数の探索フォルダ（`entries`）を階層的に管理できます。

### ① entries における name フィールドの定義
各探索パスオブジェクトには、論理名（`name` フィールド）を設定できます。
```json
"entries": [
  { "path": "src/skills", "name": "tool" },
  { "path": "src/agents", "name": "agent" }
]
```

### ② 新規スキル開発時の配置先解決
新規にスキルを自動設計・作成する際、物理的な出力先ディレクトリ（`output_dir`）を毎回直接指定する代わりに、論理名 `target_entry` を指定するだけで配置先を切り替えられます。
*   `target_entry: "agent"` ➔ `src/agents/` 配下に自動解決して新規作成
*   `target_entry: "tool"` (または未指定時のデフォルト) ➔ `src/skills/` 配下に自動解決して新規作成

`SkillsState` を介して、開発ツール（designer, coder, spec-writer）は一貫してこの決定論的パスを共有して動き、一時的なゴミフォルダの発生を抑えます。

---

## 4. `scripts/handler.py` の役割と構成

`handler.py` は、**「インターフェース層（窓口）」**としての役割のみに特化させます。

1. **`SKILL_METADATA` 定数**:
   名前、説明、実行タイプ（`tool`/`agent`）、出力モード、依存関係などのメタデータを記述します。
2. **`Input` クラス (Pydanticモデル)**:
   そのスキルが受け取る入力引数の名前、型、説明、必須フラグ、デフォルト値をPydanticスキーマとして定義します。
3. **`process_message(tool_context)` 関数**:
   統一された共通のエントリポイントです。バリデーション済みの入力オブジェクト（`Input`）を受け取り、実際のビジネスロジックモジュールへ橋渡しします。

```python
# scripts/handler.py の実装例
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .my_logic import process_message as run_logic

SKILL_METADATA = {
    "name": "my-skill",
    "description": "スキルの役割を示す1文の説明文。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

class Input(BaseModel):
    param_a: str = Field(..., description="必須のパラメータ説明")
    param_b: int = Field(10, description="デフォルト値付きパラメータ")

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 実際のビジネスロジックへ委譲し、完了メッセージを返却
    return run_logic(params, tool_context)
```

---

## 4. 共通ランナー（edd-run）によるスキーマ駆動CLI

開発者がコマンドラインから直接デバッグ・実行できるように、`edd-agent-tools` 側で**共通CLIランナー（`edd_agent_tools.run`）**を提供します。

### 仕組み
1. 指定された引数の第一位置引数から `handler.py` をロードし、`Input` スキーマと `SKILL_METADATA` を動的にインポート。
2. `Input.model_fields` から `argparse` オプションを自動生成。
3. コマンドラインからの入力を `Input.model_validate()` で型安全に検証した上で `process_message(validated_input, tool_context)` を実行。

### メリット
* **JSONエスケープ地獄の排除**: 引数はすべて通常のフラットなオプション（`--param_a value`）で書けます。
* **自動 `--help`**: `python3 -m edd_agent_tools.run my-skill --help` と打つだけで、Pydanticの定義に基づいた引数説明が自動出力されます。
* **バリデーションの即時性**: 不正な引数や型の間違いは、ビジネスロジック実行前にCLIレベルでエラーになります。
