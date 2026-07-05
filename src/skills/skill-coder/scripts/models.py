from pydantic import BaseModel, Field

class Input(BaseModel):
    prompt: str = Field(..., description='実装したいビジネスロジックの機能要件や詳細な指示。')
    skill: str | None = Field(None, description='対象のスキル名。design_pathが省略された場合の探索キー。')
    design_path: str | None = Field(None, description='対象スキルの design.json への絶対/相対パス。')
    output_dir: str | None = Field(None, description='ソースコードを出力するディレクトリ。省略時は対象スキルのルートディレクトリ。')

class Output(BaseModel):
    status: str = Field(..., description="スキルの実行結果ステータス ('success' または 'failure')")
    generated_files: list[str] = Field(..., description='生成または更新されたファイルの相対パスリスト')
    result_message: str = Field(..., description='スキル実行結果の要約メッセージ')
