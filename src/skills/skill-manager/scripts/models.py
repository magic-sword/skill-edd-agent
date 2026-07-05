from pydantic import BaseModel, Field

class Input(BaseModel):
    command: str = Field(..., description="実行するコマンド ('register', 'get-tier', 'set-tier', 'list', 'update-meta')")
    skill: str | None = Field(None, description="対象のスキル名")
    tier: int | None = Field(None, description="設定するTier (0, 1, 2, 3)")
    registry_path: str | None = Field(None, description="レジストリファイルのカスタムパス")
