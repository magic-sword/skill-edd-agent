# edd-agent-tools Implementation Examples

本ドキュメントは、`edd-agent-tools` パッケージを使用したスキルおよびエージェントの具体的な実装例や使用例をまとめたものです。

---

## 1. 統一ハンドラー規約 (`scripts/handler.py`) の実装例

```python
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic # 相対インポートを推奨

# スキルの基本メタデータ
SKILL_METADATA = {
    "name": "my-sample-skill",
    "description": "サンプルスキルの説明。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON"
}

# 要求引数を定義したスキーマ
class Input(BaseModel):
    city: str = Field(..., description="対象都市の名前")

# エントリーポイント（Input インスタンスを受け取り、完了文字列を返す）
def process_message(params: Input, tool_context: ToolContext) -> str:
    # 1. 直接ビジネスロジックを呼び出し、その結果（str）を返却する
    return run_logic(params, tool_context)
```

---

## 2. ビジネスロジック実装規約 (`scripts/logic.py`) の実装例

```python
from google.adk.tools import ToolContext
from .handler import Input
from .client import WeatherClient # 分割されたサブモジュール

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 1. パラメータは params (Input) から型安全に取得
    city = params.city
    if not city:
        raise ValueError("city is required")
        
    client = WeatherClient()
    temp_c, temp_f = client.fetch_temp(city)
    
    # 2. 状態の永続化が必要な値は tool_context.state に書き込む
    tool_context.state["celsius"] = temp_c
    tool_context.state["fahrenheit"] = temp_f
    
    # 3. AI（LLM）へのテキストフィードバックとなる実行結果サマリーを返す
    return f"Successfully fetched weather for {city}. Celsius: {temp_c}°C."

---

## 3. 主要モジュールの使用例

### ① `SkillDirectory` (パス解決とアセットロード)
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
directory = registry.get_skill_directory(name="skill-spec-writer")

# 主要パスへのアクセス
design_path = directory.design_path         # assets/design.json の絶対パス
source_code_dir = directory.source_code_dir # scripts/ の絶対パス

# アセットファイル（プロンプト等）の安全ロード
prompt_content = directory.load_asset("prompt.txt")
```

### ② `GeminiRequest` (流れるようなマルチパーツ送信)
```python
from edd_agent_tools.gemini import GeminiClient

client = GeminiClient()

# クライアント起点でリクエストを作成し、ファイルをチェーン添付してそのまま実行
response = (client.request("指示プロンプト...")
                  .add_dir(
                      directory="/workspace/src/skills/my-skill/scripts",
                      ref_root="/workspace/src/skills/my-skill",
                      file_filter=lambda path: path.endswith(".py")
                  )
                  .execute())
```

### ③ `SkillRegistry` (インプロセス解決)
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
# 相対インポートの競合なく、安全にスキルパッケージをロード
handler_module = registry.load_skill("my-sample-skill")
```
