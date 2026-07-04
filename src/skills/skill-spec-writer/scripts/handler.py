from pydantic import BaseModel, Field
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
    target_type: str = Field(..., description="生成対象のタイプ（'skill' または 'workflow'）。")
    name: str = Field(..., description="生成対象のスキルまたはワークフロー名。")
    design_path: str = Field(..., description="設計定義ファイルのパス、またはスキルのルートディレクトリ。")
    output_dir: str = Field(..., description="生成されたSKILL.mdを保存するディレクトリのパス。")
    source_code_path: str | None = Field(None, description="メインロジックのソースコードファイルパス。指定しない場合、自動的に検出を試みます。")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 既存ロジックが期待するStateパラメータを設定
    tool_context.state["target_type"] = params.target_type
    tool_context.state["name"] = params.name
    tool_context.state["design_path"] = params.design_path
    tool_context.state["output_dir"] = params.output_dir
    tool_context.state["source_code_path"] = params.source_code_path
    
    # 既存ロジックを呼び出す
    run_writer_logic(tool_context)
