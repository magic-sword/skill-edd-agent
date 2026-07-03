# edd-agent-tools パッケージ使用規約（LLM向けドキュメント）

本パッケージ `edd-agent-tools` は、Google ADK 2.0 に準拠したスキル開発を効率化し、手動CLI実行とシステム/エージェント呼び出しの両方において互換性（二重のポータビリティ）を保証するためのライブラリです。

スキルの開発においては、以下のAPIおよび状態管理のルールに必ず従ってください。

---

## 1. CLI実行ランナー: `SkillCommandLineRunner`

スキルのエントリーポイント（`if __name__ == "__main__":` ブロック）では、手続き型の引数パースを行わず、必ず `SkillCommandLineRunner` クラスを使用してください。

### 基本的な構成例
```python
from google.adk.tools import ToolContext
from edd_agent_tools.testing.cli import SkillCommandLineRunner

def process_message(tool_context: ToolContext):
    # 1. パラメータの入力取得
    user_message = tool_context.state.get("user_message", "")
    
    # 2. ビジネスロジックの実行
    result = f"Hello, {user_message}"
    
    # 3. 処理結果の出力設定
    tool_context.state["result_message"] = result

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="スキルの説明")
    # 必要に応じて独自引数を登録
    runner.add_argument("--user_message", type=str, help="ユーザーへのメッセージ")
    runner.run(process_message)
```

---

## 2. 状態管理（`tool_context.state`）のルール

`SkillCommandLineRunner` は、CLI引数（例: `--param xxx`）および JSON 形式の入力（例: `--input_json '{"param": "xxx"}'`）を**自動的にプレフィックスなしで `tool_context.state` にマージ**します。

LLMが実装するビジネスロジック内では、以下の規則に従って状態の読み書きを行ってください。

### 入力値の取得
`tool_context.state.get("引数名")` を使用して、プレフィックスなしのキーで値を取得します。
- **良例**: `skill_name = tool_context.state.get("skill_name")`
- **悪例**: `skill_name = args.skill_name` (args などのグローバル変数をビジネスロジック内で直接参照してはいけません)

### 出力値の設定
処理結果やエラー情報などは、すべて `tool_context.state["キー名"] = 値` として設定してください。
- **良例**: `tool_context.state["status"] = "success"`
- **説明**: 設定された状態は、プログラム終了時に `SkillCommandLineRunner` によって自動的に標準出力 (stdout) へJSONとして書き出され、`--output_json` が指定されている場合はファイルへも書き出されます。自前で JSON ファイルへの書き出し処理を実装する必要はありません。

---

## 3. エラー処理と終了コード

ビジネスロジック内で異常を検知した場合は、`RuntimeError` や `ValueError` などの例外（Exception）をスローしてください。
- `SkillCommandLineRunner` が例外をキャッチし、エラー内容を出力した上で、自動的に終了コード `1` でプロセスを終了させます。
- 自前で `sys.exit(1)` を呼ぶ必要はありません。
