from .models import EvaluateTriggerOutput
from .executor import SkillExecutor

def evaluate_trigger(skill: str) -> EvaluateTriggerOutput:
    """対象スキルの仕様書（SKILL.md）を静的に評価し、トリガー評価用のポジティブ・ネガティブテストケースを自動生成・保存します。

    Args:
        skill: トリガーアセット生成および評価対象のスキル名。

    Returns:
        実行結果オブジェクト (EvaluateTriggerOutput)。
    """
    executor = SkillExecutor()
    return executor.evaluate_trigger(skill=skill)

