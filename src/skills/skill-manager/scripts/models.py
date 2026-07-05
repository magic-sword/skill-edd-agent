from pydantic import BaseModel, Field
from typing import Literal

class Input(BaseModel):
    command: Literal['register', 'get-tier', 'set-tier', 'list', 'update-meta'] = Field(..., description='実行するコマンド')
    skill: str | None = Field(None, description='対象のスキル名')
    tier: Literal['0', '1', '2', '3'] | None = Field(None, description='設定するTier')
    registry_path: str | None = Field(None, description='レジストリファイルのカスタムパス')

class Output(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')
