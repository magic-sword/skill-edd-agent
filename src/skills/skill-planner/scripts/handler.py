from .models import SkillPlannerOutput
from .executor import SkillPlannerExecutor

def skill_planner(prompt: str) -> SkillPlannerOutput:
    """ユーザーの要件プロンプトから、単体スキル（skill）、ワークフロー（workflow）、または事前スキル提案（proposal）かを分析・評価して計画立案します。

    Args:
        prompt: 開発したい機能の要件プロンプト。

    Returns:
        実行結果オブジェクト (SkillPlannerOutput)。
    """
    executor = SkillPlannerExecutor()
    return executor.plan_requirement(prompt=prompt)
