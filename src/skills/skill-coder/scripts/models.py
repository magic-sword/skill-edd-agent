from pydantic import BaseModel, Field
from edd_agent_tools.models import PromptField

class Input(BaseModel):
    prompt: str | None = PromptField(None, description='実装したいビジネスロジックの機能要件や詳細な指示。', instructions='生成・修正したいビジネスロジック（例：APIクライアントの作成、バリデーションロジックの追加、ユーティリティ関数の実装など）の実装要件を指定できます。', constraints='自動生成される handler.py, models.py, __init__.py, workflow.py は編集できません。また、エグゼキューター（scripts/executor.py）の全体的なクラス構造やインターフェース（execute() メソッド）は固定されているため、これを逸脱するシグネチャ変更はできません。')
    skill: str | None = Field(None, description='対象のスキル名。design_pathが省略された場合の探索キー。')
    design_path: str | None = Field(None, description='対象スキルの design.json への絶対/相対パス。')
    output_dir: str | None = Field(None, description='ソースコードを出力するディレクトリ。省略時は対象スキルのルートディレクトリ。')

class Output(BaseModel):
    status: str = Field(..., description="スキルの実行結果ステータス ('success' または 'failed')")
    message: str = Field(..., description='スキル実行結果の要約メッセージ')
    output_dir: str = Field(..., description='実装コードが出力されたディレクトリの絶対パス')
