from pydantic import BaseModel, Field, model_validator
from google.adk.tools import ToolContext
from .spec_writer import process_message as run_writer_logic

SKILL_METADATA = {
    "name": "skill-spec-writer",
    "description": "設計情報（Pydanticスキーマ等）を動的にロードし、ADK 2.0仕様に準拠したSKILL.mdを生成します。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

class Input(BaseModel):
    design_path: str | None = Field(None, description="design.json ファイルの直接のパス。省略された場合は skill から自動探索します。")
    skill: str | None = Field(None, description="対象の既存スキル名。design_path 省略時の自動探索キーとして使用されます。")
    output_dir: str | None = Field(None, description="生成されたSKILL.mdを保存するディレクトリのパス。省略時は対象スキルのディレクトリに出力されます。")
    source_code_dir: str | None = Field(None, description="実装ソースコードが格納されたディレクトリパス（または単一ファイル）。指定しない場合、自動的にスキルの scripts ディレクトリを探索します。")

    @model_validator(mode="after")
    def check_skill_or_design_path(self) -> "Input":
        """skill と design_path のいずれか一方は必ず指定する必要があります。"""
        if not self.skill and not self.design_path:
            raise ValueError("Either 'skill' or 'design_path' must be provided.")
        return self

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_writer_logic(params, tool_context)
