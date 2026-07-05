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

# エントリーポイント
def process_message(tool_context: ToolContext):
    # 1. バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 2. 引数を state に移行
    if params:
        for key, value in params.model_dump().items():
            if value is not None:
                tool_context.state[key] = value
                
    # 3. ビジネスロジックを呼び出す
    run_logic(tool_context)
```

---

## 2. ビジネスロジック実装規約 (`scripts/logic.py`) の実装例

```python
from google.adk.tools import ToolContext
from .client import WeatherClient # 分割されたサブモジュール

def process_message(tool_context: ToolContext):
    city = tool_context.state.get("city")
    if not city:
        raise ValueError("city is required")
        
    client = WeatherClient()
    temp_c, temp_f = client.fetch_temp(city)
    
    # 結果は必ず state に直接書き込む (戻り値を return しない)
    tool_context.state["celsius"] = temp_c
    tool_context.state["fahrenheit"] = temp_f
```

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

### ② `GeminiContentBuilder` (マルチパーツ送信)
```python
from edd_agent_tools.gemini import GeminiContentBuilder

builder = GeminiContentBuilder("指示プロンプト...")
# 指定ディレクトリのPythonファイルを添付パーツとして追加
builder.add_dir(
    directory="/workspace/src/skills/my-skill/scripts",
    ref_root="/workspace/src/skills/my-skill",
    file_filter=lambda path: path.endswith(".py")
)
# generate_content に渡すマルチパーツのリストを取得
contents = builder.build()
```

### ③ `SkillRegistry` (インプロセス解決)
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
# 相対インポートの競合なく、安全にハンドラーモジュールをロード
handler_module = registry.load_handler("my-sample-skill")
```
