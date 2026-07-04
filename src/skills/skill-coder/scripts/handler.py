from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "skill-coder",
    "description": "設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コード(scripts/handler.py, scripts/logic.py等)を自動生成・更新するスキル",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

class Input(BaseModel):
    prompt: str = Field(..., description='実装したいビジネスロジックの機能要件や詳細な指示。')
    name: str | None = Field(None, description='対象のスキル名。design_pathが省略された場合の探索キー。')
    design_path: str | None = Field(None, description='対象スキルの design.json への絶対/相対パス。')
    output_dir: str | None = Field(None, description='ソースコードを出力するディレクトリ。省略時は対象スキルのルートディレクトリ。')

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # Stateパラメータを移行
    if params:
        for key, value in params.model_dump().items():
            if value is not None:
                tool_context.state[key] = value
            
    # ビジネスロジックを呼び出す
    run_logic(tool_context)
