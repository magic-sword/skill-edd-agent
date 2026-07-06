from pydantic import BaseModel, Field
from edd_agent_tools.models import PromptField
from typing import Literal

class Input(BaseModel):
    prompt: str = PromptField(..., description='スキル設計・実装の要件', instructions='生成したいスキルの機能、目的、入出力、制約、利用シナリオなどを具体的に記述してください。', constraints='破壊的な操作や機密情報に関わる指示は避けてください。生成されるスキルはADK 2.0規約に準拠する必要があります。')
    skill: str | None = Field(None, description='対象のスキル名')
    output_dir: str | None = Field(None, description='成果物の出力先ディレクトリ')
    design_path: str | None = Field(None, description='design.jsonの絶対パス')
    source_code_dir: str | None = Field(None, description='実装コードのソースコードディレクトリ')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description='処理結果の成否ステータス')
    message: str = Field(..., description='処理結果のメッセージサマリー')
    output_dir: str = Field(..., description='最終生成された成果物が格納されたスキルディレクトリの絶対パス')
