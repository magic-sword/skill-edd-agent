from pydantic import BaseModel, Field, model_validator
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
    output_dir: str | None = Field(None, description="生成されたdesign.jsonを保存するディレクトリのパス。省略時はskillから自動探索されます。")
    skill: str | None = Field(None, description="既存のスキル名。再設計時の自動探索キーとして使用されます。")
    source_code_dir: str | None = Field(None, description="再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。指定しない場合、自動的に検出を試みます。")

    @model_validator(mode="after")
    def check_output_dir_or_skill(self) -> "Input":
        """output_dir と skill のいずれか一方は必ず指定する必要があります。"""
        if not self.output_dir and not self.skill:
            raise ValueError("Either 'output_dir' or 'skill' must be provided.")
        return self

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 既存ロジックが期待するStateパラメータを設定
    tool_context.state["requirement"] = params.requirement
    tool_context.state["output_dir"] = params.output_dir
    tool_context.state["skill"] = params.skill
    tool_context.state["source_code_dir"] = params.source_code_dir
    
    # 既存ロジックを呼び出す
    run_designer_logic(tool_context)
