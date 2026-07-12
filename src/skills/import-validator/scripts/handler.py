from .models import Output
from .executor import SkillExecutor

def validate_skill_import(skill: str) -> dict:
    """指定されたスキルを動的にインポートし、その成否を検証します。

    Args:
        skill: ロードを試みる対象のスキル名。

    Returns:
        検証結果（status, details, score）を含む辞書。
    """
    executor = SkillExecutor(skill=skill)
    result = executor.execute()
    return result.model_dump()
