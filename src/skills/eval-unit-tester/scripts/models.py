from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description="単体テストを生成する対象のスキル名。")
