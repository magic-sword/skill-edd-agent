# edd-agent-tools パッケージ使用規約（LLM向けドキュメント）

本パッケージ `edd-agent-tools` は、Google ADK 2.0 に準拠したスキル開発を効率化し、手動CLI実行とシステム/エージェント呼び出しの両方において完全な互換性と安全なインプロセス実行を保証するためのライブラリです。

スキルの開発および統合においては、以下のルールに必ず従ってください。

---

## 1. 統一ハンドラー規約 (`scripts/handler.py`)

すべてのスキルおよびエージェントは、エントリーポイントおよびインターフェース定義を **`scripts/handler.py`** に統一しなければなりません。このファイルには以下の3つの要素を定義します。

1. **`SKILL_METADATA`** (辞書):
   スキルの基本メタデータ（名前、説明、実行形式、出力モード等）。
2. **`Input`** (Pydantic `BaseModel`):
   スキルが受け取る引数を定義した入力スキーマ。型ヒント、必須/任意の制約、および `Field` による説明文を含めます。
3. **`process_message(tool_context: ToolContext)`** (関数):
   スキルのメインビジネスロジック。型検証済みの入力パラメータオブジェクト（`tool_context.state["validated_input"]`）を受け取って処理を実行します。

### 基本的な構成例 (`scripts/handler.py`)
```python
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import execute_business_logic # 相対インポートを推奨

SKILL_METADATA = {
    "name": "my-sample-skill",
    "description": "サンプルスキルの説明文。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON"
}

class Input(BaseModel):
    requirement: str = Field(..., description="指示内容の自然言語テキスト。")
    output_dir: str = Field(..., description="成果物を保存するディレクトリの絶対パス。")

def process_message(tool_context: ToolContext):
    # 1. バリデーション済みのPydanticオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 2. ビジネスロジックの呼び出し (handler.py 自体は薄く保つ)
    result = execute_business_logic(params.requirement, params.output_dir)
    
    # 3. 処理結果を状態に設定
    tool_context.state.update(result)
```

---

## 2. 状態管理（`tool_context.state`）とスキーマ駆動

* **入力値の取得**:
  共通CLIランナーは、Pydanticの `Input` スキーマに基づいてコマンドライン引数を動的パース・バリデーションし、パース後のオブジェクトを `validated_input` という名前で `tool_context.state` にバインドします。ビジネスロジック内では、必ず `tool_context.state.get("validated_input")` を使用して安全に入力を取得してください。
* **出力値の設定**:
  処理結果や出力メタデータは、すべて `tool_context.state["キー名"] = 値` として設定してください。共通CLIランナーが自動的に標準出力やファイル（`--output_json`）にJSONとして書き出します。

---

## 3. エラー処理と終了コード

ビジネスロジック内で異常（要件の違反、実行時エラー等）を検知した場合は、`ValueError` や `RuntimeError` などの例外（Exception）をスローしてください。
* 共通CLIランナーが自動的に例外をキャッチし、エラー内容を出力した上で、終了コード `1` で安全にプロセスを終了させます。
* 自前で `sys.exit(1)` を呼ぶ必要はありません。

---

## 4. スキルの動的ロードと解決: `SkillRegistry`

ワークフローの実行スクリプトやシステム側（実行エンジン）でスキルをインプロセスでロードする際は、`skills_registry.json` に基づいてロードを制御する `SkillRegistry` クラスを使用してください。

`SkillRegistry.load_handler(skill_name)` は、キャッシュ競合を避けるために一意の名前空間（仮想FQDN）の配下にハンドラーモジュールを登録してロードします。これにより、同一プロセス内で複数のスキルを順次ロードしても、モジュールが干渉することなく安全に動作します。

### 基本的な解決例
```python
from edd_agent_tools.registry import SkillRegistry

# レジストリの初期化 (デフォルトで /workspace/src/skills_registry.json を対象とします)
registry = SkillRegistry()

# 1. 登録されているスキルの handler モジュールを安全にロード
handler_module = registry.load_handler("my-sample-skill")

# 2. ロードしたモジュールからスキーマやエントリーポイントを呼び出し
InputSchema = getattr(handler_module, "Input")
process_message = getattr(handler_module, "process_message")
```

---

## 5. 同期コマンド実行インプロセスツール: `run_system_command`

エージェントが評価テストの実行（`adk eval`など）や、時間のかかるシェルコマンドを実行する際、システムが提供する `run_command` は10秒の制限を超えると非同期（バックグラウンド）実行になりエージェントがスタックする原因になります。

これを回避するために、`edd-agent-tools` が提供する同期コマンド実行用インプロセスツール `run_system_command` をインプロセスツールとしてバインドして実行させてください。

### 基本的な構成例
```python
from edd_agent_tools.utils import run_system_command
from google.adk.tools import ToolContext

# ToolContext 内の state に実行したいコマンドを設定します
tool_context = ToolContext()
tool_context.state["command"] = "adk eval /workspace/src /workspace/src/tests/evalset.json"
tool_context.state["cwd"] = "/workspace"
tool_context.state["timeout_seconds"] = 180

# 同期実行 (コマンド完了までブロックして出力を返します)
output_message = run_system_command(tool_context)
print(output_message)
```
