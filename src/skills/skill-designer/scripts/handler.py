from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .skill_designer import process_message as run_designer_logic

SKILL_METADATA = {
    "name": "skill-designer",
    "description": "スキル設計要件に基づいて新しいスキルを設計し、または既存スキルを再設計するツール。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

class Input(BaseModel):
    requirement: str = Field(..., description="設計するスキルの機能要件を記述した自然言語のテキスト。")
    output_dir: str = Field(..., description="生成されたdesign.jsonを保存するディレクトリのパス。")
    source_code_path: str | None = Field(None, description="再設計のベースとなる既存のスキル実装コードのファイルパス。指定しない場合、自動的に検出を試みます。")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 既存ロジックが期待するStateパラメータを設定
    tool_context.state["requirement"] = params.requirement
    tool_context.state["output_dir"] = params.output_dir
    tool_context.state["source_code_path"] = params.source_code_path
    
    # 既存ロジックを呼び出す
    run_designer_logic(tool_context)
