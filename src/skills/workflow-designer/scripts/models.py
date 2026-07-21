from pydantic import BaseModel, Field

class WorkflowDesignerOutput(BaseModel):
    status: str = Field(..., description="処理結果の成否ステータス（'success' / 'failed'）")
    message: str = Field(..., description="処理結果のメッセージサマリー")
    output_dir: str = Field(..., description="成果物(design.json)が格納されたディレクトリの絶対パス")
    design_path: str = Field("", description="生成された design.json の絶対パス")
