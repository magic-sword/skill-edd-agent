from pydantic import BaseModel, Field
from typing import Literal, Optional


class ProposedSkill(BaseModel):
    name: str = Field(..., description="提案する事前開発スキルの名前（ケバブケース推奨、例: 'log-parser'）。")
    description: str = Field(..., description="提案する事前開発スキルの具体的な役割・機能要件の説明。")


class SkillPlannerOutput(BaseModel):
    route: Literal['create_skill', 'create_workflow', 'update_skill', 'update_workflow', 'proposal'] = Field(
        ...,
        description="判定された開発ルート（'create_skill': 新規単体スキル, 'create_workflow': 新規ワークフロー, 'update_skill': 既存の単体スキル化更新, 'update_workflow': 既存のワークフロー化更新, 'proposal': 事前提案）。"
    )
    target_skill: Optional[str] = Field(
        default=None,
        description="route が 'update_skill' または 'update_workflow' の場合に特定された既存スキル/ワークフローの名前。"
    )
    rationale: str = Field(..., description="そのルートに決定した分析理由。")
    recommended_dependencies: list[str] = Field(
        default_factory=list,
        description="ワークフローの場合に推奨される既存スキル名のリスト。"
    )
    proposed_skill: Optional[ProposedSkill] = Field(
        default=None,
        description="route が 'proposal' の場合に提案される、事前に開発しておくべき単体スキルの情報。"
    )
