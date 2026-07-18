from pydantic import BaseModel, Field


class EvaluateTriggerOutput(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')
    status: str = Field(..., description='実行ステータス (success/failed)')
    eval_set_path: str = Field(..., description='生成された評価用アセットファイルパス')
