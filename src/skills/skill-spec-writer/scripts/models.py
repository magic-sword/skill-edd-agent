from pydantic import BaseModel, Field
from typing import Literal

class Input(BaseModel):
    design_path: str | None = Field(None, description='design.json ファイルの直接のパス。省略された場合は skill から自動探索します。')
    skill: str | None = Field(None, description='対象の既存スキル名。design_path 省略時の自動探索キーとして使用されます。')
    output_dir: str | None = Field(None, description='生成されたSKILL.mdを保存するディレクトリのパス。省略時は対象スキルのディレクトリに出力されます。')
    source_code_dir: str | None = Field(None, description='実装ソースコードが格納されたディレクトリパス（または単一ファイル）。指定しない場合、自動的にスキルの scripts ディレクトリを探索します。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="スキルの実行結果ステータス。'success' または 'failed'。")
    message: str = Field(..., description='実行結果に関する詳細メッセージ。')
    output_file_path: str | None = Field(None, description='生成されたSKILL.mdファイルの絶対パス。成功時にのみ存在し、失敗時はnull。')
