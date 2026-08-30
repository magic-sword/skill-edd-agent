"""
Skill Logic Draft Models for edd-agent-tools
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from .spec import SkillPattern


class DecisionBranch(BaseModel):
    """意思決定ツリーの分岐ルール"""
    condition: str = Field(..., description="分岐条件 (例: 入力ファイルがPDF形式の場合)")
    action: str = Field(..., description="実行するアクションまたは参照先 (例: scripts/rotate_pdf.py を実行)")


class StepInstruction(BaseModel):
    """動詞起点 (Imperative) の実行手順"""
    step_number: int = Field(..., description="ステップ番号 (1始まり)")
    title: str = Field(..., description="ステップの見出し (動詞起点)")
    action_imperative: str = Field(..., description="具体的な手順指示 (To do X, execute Y 形式)")
    target_resource: Optional[str] = Field(None, description="使用するスクリプトまたは参照資料の相対パス")


class ResourcePlan(BaseModel):
    """3層リソース (scripts, references, assets) の計画定義"""
    rel_path: str = Field(..., description="ファイル相対パス (例: scripts/convert.py, references/schema.md)")
    type: Literal["script", "reference", "asset"] = Field(..., description="リソース種別")
    purpose: str = Field(..., description="このリソースが果たす役割と内容")


class SkillLogicDraft(BaseModel):
    """Stage 1: LLMが要件から抽出する論理設計データモデル。

    Markdownのレイアウトに依存せず、設計の骨子（認知的知識、決定木、リソース計画、非適用条件）のみを型安全に抽出します。
    """
    name: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="ハイフンケースのスキル名 (例: pdf-tools, api-helper)")
    pattern: SkillPattern = Field(..., description="4パターンのいずれか")
    description_third_person: str = Field(..., max_length=1024, description="第三者視点でのトリガー説明 ('This skill should be used when...')")
    concrete_trigger_examples: List[str] = Field(..., min_length=2, max_length=6, description="具体的なユーザー発話・トリガー例")
    when_not_to_use: List[str] = Field(default_factory=list, description="誤発火を防ぐための非適用条件（When NOT to use）")
    overview_summary: str = Field(..., description="スキルの目的・提供価値の簡潔な要約 (1〜2文)")
    decision_tree: List[DecisionBranch] = Field(default_factory=list, description="条件分岐ルール")
    execution_steps: List[StepInstruction] = Field(..., min_length=1, description="動詞起点の実行手順リスト")
    dependencies: List[str] = Field(default_factory=list, description="依存する他のスキル名のリスト")
    resources_plan: List[ResourcePlan] = Field(default_factory=list, description="3層リソースの計画一覧")
    guidelines: List[str] = Field(default_factory=list, description="実行時の注意点・ベストプラクティス")
