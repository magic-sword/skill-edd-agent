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
    skill: str | None = Field(None, description='対象のスキル名。design_pathが省略された場合の探索キー。')
    design_path: str | None = Field(None, description='対象スキルの design.json への絶対/相対パス。')
    output_dir: str | None = Field(None, description='ソースコードを出力するディレクトリ。省略時は対象スキルのルートディレクトリ。')

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
