from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description="トリガーアセット生成および評価対象のスキル名。")
