from .executor import SkillExecutor

def evaluate_trigger(skill: str) -> dict:
    """対象スキルの仕様書（SKILL.md）を静的に具体性と明確性の観点から評価し、トリガー評価用のポジティブ・ネガティブテストケースを自動生成・保存します。

    Args:
        skill: トリガーアセット生成および評価対象のスキル名。

    Returns:
        実行結果（value, status, eval_set_path）を含む辞書。
    """
    executor = SkillExecutor(skill=skill)
    result = executor.execute()
    return result.model_dump()
