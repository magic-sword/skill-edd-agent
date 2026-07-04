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

## 3. `scripts/handler.py` の役割と構成

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
from .my_logic import run_business_logic

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

def process_message(tool_context: ToolContext):
    # 共通ランナーによって検証されたオブジェクトを型安全に取得
    params: Input = tool_context.state.get("validated_input")
    
    # 実際のビジネスロジックへ委譲
    run_business_logic(params, tool_context)
```

---

## 4. 共通ランナー（`edd-run`）によるスキーマ駆動CLI

開発者がコマンドラインから直接デバッグ・実行できるように、`edd-agent-tools` 側で**共通CLIランナー（`edd_agent_tools.cli.run`）**提供します。

### 仕組み
1. 指定された `--skill_name` から `handler.py` の `Input` と `SKILL_METADATA` を動的にインポート。
2. `Input.model_fields` から `argparse` オプションを自動生成。
3. コマンドラインからの入力を `Input.model_validate()` で型安全に検証した上で `process_message` を実行。

### メリット
* **JSONエスケープ地獄の排除**: 引数はすべて通常のフラットなオプション（`--param_a value`）で書けます。
* **自動 `--help`**: `python3 -m edd_agent_tools.cli.run --skill_name my-skill --help` と打つだけで、Pydanticの定義に基づいた引数説明が自動出力されます。
* **バリデーションの即時性**: 不正な引数や型の間違いは、ビジネスロジック実行前にCLIレベルでエラーになります。
