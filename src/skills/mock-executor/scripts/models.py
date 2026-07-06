from pydantic import BaseModel, Field
from edd_agent_tools.models import PromptField

class Input(BaseModel):
    skill: str = PromptField(..., description='評価対象スキルの名前。', instructions='評価を実行したいスキルの名前を正確に指定してください。', constraints='必須項目です。')
    eval_set_path: str = PromptField('trigger', description="評価セットの識別子（'trigger' または 'unit'）、あるいはファイルパス。デフォルトは 'trigger'。", instructions="評価セットのタイプ（'trigger' または 'unit'）を指定するか、評価セットファイルへのパスを指定してください。", constraints="デフォルトは 'trigger' です。")
    config_file_path: str | None = Field(None, description='評価設定ファイルのパス。指定しない場合は自動解決・自動生成されます。')
    timeout_seconds: int = Field(180, description='評価のタイムアウト秒数。デフォルトは 180 秒。')
    threshold_accuracy: float = Field(1.0, ge=0.0, le=1.0, description='合格に必要な精度の閾値（0.0 から 1.0）。デフォルトは 1.0。')

class Output(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')
