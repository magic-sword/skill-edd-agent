from pydantic import BaseModel, Field
from typing import Literal, Optional


class ProposedSkill(BaseModel):
    name: str = Field(..., description="提案する事前開発スキルの名前（ケバブケース推奨、例: 'log-parser'）。")
    description: str = Field(..., description="提案する事前開発スキルの具体的な役割・機能要件の説明。")


class DeveloperRouterOutput(BaseModel):
    route: Literal['skill', 'workflow', 'proposal'] = Field(
        ...,
        description="判定された開発ルート（'skill': 単体スキル, 'workflow': ワークフロー, 'proposal': 事前スキル開発の提案）。"
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

