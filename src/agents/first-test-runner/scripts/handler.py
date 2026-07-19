from .models import RunFirstTestOutput
from .executor import SkillExecutor

def run_first_test(skill: str) -> RunFirstTestOutput:
    """指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録します。

    Args:
        skill: 試験対象のスキル名。

    Returns:
        実行結果オブジェクト (RunFirstTestOutput)。
    """
    executor = SkillExecutor()
    return executor.run_first_test(skill=skill)

