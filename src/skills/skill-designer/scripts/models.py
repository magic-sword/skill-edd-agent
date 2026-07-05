from pydantic import BaseModel, Field
from edd_agent_tools.models import PromptField
from typing import Literal

class Input(BaseModel):
    prompt: str = PromptField(..., description='設計するスキルの機能要件や追加の改修要望を記述した自然言語のテキスト。', instructions='新しく作りたいスキルの概要説明、パラメータ定義、実行タイプ（tool/agent）、制約事項などを自然言語で指示できます。また、既存コードへの機能追加要望も指定可能です。', constraints='設計書（design.json）の全体構造（スキーマ定義）はADK 2.0規約に基づいてバリデーションされるため、規約違反となるような無効なフィールド定義を出力させることはできません。')
    summary: str | None = PromptField(None, description='スキルの仕様概要（ビジネス目的や要求の要約）。指定した場合、Geminiによる自動要約より優先して design.json の summary フィールドに保存されます。', instructions='スキルのビジネス目的や提供価値を要約した、簡潔な日本語の1〜2文を設定・上書きできます。', constraints='値はそのまま design.json の summary フィールドに直接流し込まれ、他の構造の生成には影響を与えません。')
    output_dir: str | None = Field(None, description='生成されたdesign.jsonを保存するディレクトリのパス。省略時はskillから自動探索されます。')
    skill: str | None = Field(None, description='既存のスキル名。再設計時の自動探索キーとして使用されます。')
    source_code_dir: str | None = Field(None, description='再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。指定しない場合、自動的に検出を試みます。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="処理結果の成否ステータス（'success' / 'failed'）")
    message: str = Field(..., description='処理結果のメッセージサマリー')
    output_file_path: str = Field(..., description='生成された design.json の絶対ファイルパス')
