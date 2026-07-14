from pydantic import BaseModel, Field
from edd_agent_tools import PromptField
from typing import Literal

class Input(BaseModel):
    prompt: str = PromptField(..., description='スキル設計・実装の要件を記述したプロンプト。', instructions='スキル設計・実装の要件を具体的に記述してください。どのような機能を持つスキルが必要か、どのような入力と出力を期待するか、どのような制約があるかなどを明確に指定してください。', constraints='スキル設計・実装の要件は、明確かつ具体的な指示である必要があります。曖昧な表現や矛盾する指示は避けてください。また、セキュリティやプライバシーに関する要件がある場合は明記してください。')
    skill: str | None = Field(None, description='対象のスキル名。既存スキルを改修する場合に指定します。')
    output_dir: str | None = Field(None, description='成果物の出力先ディレクトリのパス。')
    design_path: str | None = Field(None, description='design.jsonの絶対パス。既存スキルを改修する場合に指定します。')
    source_code_dir: str | None = Field(None, description='実装コードのソースコードディレクトリのパス。既存スキルを改修する場合に指定します。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description='処理結果の成否ステータス。')
    message: str = Field(..., description='処理結果のメッセージサマリー。')
    output_dir: str = Field(..., description='最終生成された成果物が格納されたスキルディレクトリの絶対パス。')
