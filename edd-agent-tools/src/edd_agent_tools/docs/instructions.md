# edd-agent-tools パッケージ使用規約（LLM向けドキュメント）

本パッケージ `edd-agent-tools` は、Google ADK 2.0 に準拠したスキル開発を効率化し、手動CLI実行とシステム/エージェント呼び出しの両方において互換性（二重のポータビリティ）を保証するためのライブラリです。

スキルの開発においては、以下のAPIおよび状態管理のルールに必ず従ってください。

---

## 1. エントリーポイントの統一 (`scripts/main.py`) と CLI・ビジネスロジックの分離

すべてのスキルは、以下の2つの役割（ファイル）に厳密に分離し、エントリーポイントを **`scripts/main.py`** に統一しなければなりません。

1.  **ビジネスロジックモジュール (`scripts/[skill_name_with_underscores].py`)**:
    *   純粋な Python モジュールとして、ビジネスロジックである `process_message` などの関数定義のみを記述します。
    *   このファイル内に `if __name__ == "__main__":` や `SkillCommandLineRunner`、引数パース、副作用のあるグローバル処理は**記述してはいけません**。
2.  **CLIエントリーポイントラッパー (`scripts/main.py`)**:
    *   `SkillCommandLineRunner` を使用して CLI の引数パースと実行を行うだけの軽量なラッパーファイルです。
    *   ビジネスロジック関数（`process_message` など）をインポートして公開（エクスポート）します。

### 基本的な構成例

**ビジネスロジック側 (`scripts/my_skill.py`)**:
```python
from google.adk.tools import ToolContext

def process_message(tool_context: ToolContext):
    # 1. パラメータの入力取得
    user_message = tool_context.state.get("user_message", "")
    
    # 2. ビジネスロジックの実行
    result = f"Hello, {user_message}"
    
    # 3. 処理結果の出力設定
    tool_context.state["result_message"] = result
```

**CLIエントリーポイント側 (`scripts/main.py`)**:
```python
import sys
from edd_agent_tools.testing import SkillCommand, CommandLineRunner

# 動的パス操作（sys.path.insert 等）は行わず、相対インポートを使用
from .my_skill import process_message

if __name__ == "__main__":
    cmd = SkillCommand.from_argv("my-skill", sys.argv[1:])
    runner = CommandLineRunner(cmd)
    runner.run(process_message)
```

---

## 2. 状態管理（`tool_context.state`）のルール

`CommandLineRunner` と `SkillCommand` の組み合わせは、CLI引数（例: `--param xxx`）および JSON 形式の入力（例: `--input_json '{"param": "xxx"}'`）を**自動的にプレフィックスなしで `tool_context.state` にマージ**します。

LLMが実装するビジネスロジック内では、以下の規則に従って状態の読み書きを行ってください。

### 入力値の取得
`tool_context.state.get("引数名")` を使用して、プレフィックスなしのキーで値を取得します。
- **良例**: `skill_name = tool_context.state.get("skill_name")`
- **悪例**: `skill_name = args.skill_name` (args などのグローバル変数をビジネスロジック内で直接参照してはいけません)

### 出力値の設定
処理結果やエラー情報などは、すべて `tool_context.state["キー名"] = 値` として設定してください。
- **良例**: `tool_context.state["status"] = "success"`
- **説明**: 設定された状態は、プログラム終了時に `CommandLineRunner` によって自動的に標準出力 (stdout) へJSONとして書き出され、`--output_json` が指定されている場合はファイルへも書き出されます。自前で JSON ファイルへの書き出し処理を実装する必要はありません。

---

## 3. エラー処理と終了コード

ビジネスロジック内で異常を検知した場合は、`RuntimeError` や `ValueError` などの例外（Exception）をスローしてください。
- `CommandLineRunner` が例外をキャッチし、エラー内容を出力した上で、自動的に終了コード `1` でプロセスを終了させます。
- 自前で `sys.exit(1)` を呼ぶ必要はありません。

---

## 4. スキルレジストリ操作と動的解決: `SkillRegistry`

ワークフローの実行スクリプトやスキル管理ツールなどの「システム側（実行エンジン）」では、`skills_registry.json` に登録されたスキルの操作やインプロセスツールの動的ロードに `SkillRegistry` クラスを使用してください。

`SkillRegistry.load_tool` は、指定されたスキルの **`scripts/main.py`** を自動的に動的ロードし、そこから関数オブジェクトを取得します。

### 基本的な構成例
```python
from edd_agent_tools.registry import SkillRegistry

# レジストリの初期化 (デフォルトで /workspace/src/skills_registry.json を対象とします)
registry = SkillRegistry()

# 1. 登録されているスキルのインプロセスツールを動的解決・ロード
# (scripts/main.py から set_skill_tier がインポート・エクスポートされます)
set_skill_tier = registry.load_tool("skill-manager", "set_skill_tier")

# 2. 登録スキルの一覧取得・管理
registry.list_skills()
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
tool_context.state["command"] = "python src/skills/eval-unit-tester/scripts/eval_unit_tester.py --skill_name skill-generator"
tool_context.state["cwd"] = "/workspace"
tool_context.state["timeout_seconds"] = 120

# 同期実行 (コマンド完了までブロックして出力を返します)
output_message = run_system_command(tool_context)
print(output_message)
```

