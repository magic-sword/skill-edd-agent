from pydantic import BaseModel, Field

class Input(BaseModel):
    output_dir: str = Field(..., description="生成されたスキルが出力されるディレクトリのパス。例: src/skills/my-skill")
    prompt: str = Field(..., description="生成したいスキルの詳細な説明や要件。")
    model: str = Field("gemini-2.5-flash", description="使用するモデル名。")
    max_attempts: int = Field(15, description="サブエージェントの最大試行ターン数。")
