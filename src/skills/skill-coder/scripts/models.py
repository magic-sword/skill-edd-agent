from pydantic import BaseModel, Field

class Output(BaseModel):
    status: str = Field(..., description="スキルの実行結果ステータス ('success' または 'failed')")
    message: str = Field(..., description='スキル実行結果の要約メッセージ')
    output_dir: str = Field(..., description='実装コードが出力されたディレクトリの絶対パス')
