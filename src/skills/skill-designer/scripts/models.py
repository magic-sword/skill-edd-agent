from pydantic import BaseModel, Field

class Input(BaseModel):
    prompt: str = Field(..., description='設計するスキルの機能要件や追加の改修要望を記述した自然言語のテキスト。')
    summary: str | None = Field(None, description='スキルの仕様概要（ビジネス目的や要求の要約）。指定した場合、Geminiによる自動要約より優先して design.json の summary フィールドに保存されます。')
    output_dir: str | None = Field(None, description='生成されたdesign.jsonを保存するディレクトリのパス。省略時はskillから自動探索されます。')
    skill: str | None = Field(None, description='既存のスキル名。再設計時の自動探索キーとして使用されます。')
    source_code_dir: str | None = Field(None, description='再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。指定しない場合、自動的に検出を試みます。')

class Output(BaseModel):
    status: str = Field(..., description="処理結果の成否ステータス（'success' / 'failed'）")
    message: str = Field(..., description='処理結果のメッセージサマリー')
    output_file_path: str = Field(..., description='生成された design.json の絶対ファイルパス')
