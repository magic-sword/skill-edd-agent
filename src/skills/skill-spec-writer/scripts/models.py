from pydantic import BaseModel, Field
from typing import Literal
from edd_agent_tools.models import PromptField

class Input(BaseModel):
    prompt: str | None = PromptField(
        None,
        description='仕様書生成における、特別に明記したい追加の表現上のこだわりや注意点などの指示。',
        instructions='生成される仕様書のテキスト説明のトーンや粒度（例: 開発者向けに詳細に、あるいは初心者向けに簡単に書く）、特別に言及してほしいセキュリティ設計や注意点の強調を指定できます。',
        constraints='仕様書のマークダウンレイアウト構成（見出しの順序、テーブル項目）は決定論的テンプレートに固定されているため、プロンプト指示によって構成そのものを変更することはできません。'
    )
    design_path: str | None = Field(None, description='design.json ファイルの直接のパス。省略された場合は skill から自動探索します。')
    skill: str | None = Field(None, description='対象の既存スキル名。design_path 省略時の自動探索キーとして使用されます。')
    output_dir: str | None = Field(None, description='生成されたSKILL.mdを保存するディレクトリのパス。省略時は対象スキルのディレクトリに出力されます。')
    source_code_dir: str | None = Field(None, description='実装ソースコードが格納されたディレクトリパス（または単一ファイル）。指定しない場合、自動的にスキルの scripts ディレクトリを探索します。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="スキルの実行結果ステータス。'success' または 'failed'。")
    message: str = Field(..., description='実行結果に関する詳細メッセージ。')
    output_dir: str = Field(..., description='仕様書(SKILL.md)が格納されたスキルディレクトリの絶対パス')
