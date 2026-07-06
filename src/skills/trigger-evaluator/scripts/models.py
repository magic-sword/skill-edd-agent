from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description='トリガーアセット生成および評価対象のスキル名。')

class Output(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')
