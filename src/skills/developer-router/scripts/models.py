from pydantic import BaseModel, Field
from typing import Literal

class DeveloperRouterOutput(BaseModel):
    route: Literal['skill', 'workflow'] = Field(..., description="判定された開発ルート（'skill' または 'workflow'）。")
    rationale: str = Field(..., description="そのルートに決定した分析理由。")
    recommended_dependencies: list[str] = Field(default_factory=list, description="ワークフローの場合に推奨される既存スキル名のリスト。単体スキルの場合は空リストになります。")
