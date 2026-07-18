from .models import ValidateDesignOutput
from .executor import SkillExecutor

def validate_design(skill: str) -> ValidateDesignOutput:
    """設計仕様と実装の整合性を検証します。

    Args:
        skill: 検証対象のスキル名。小文字のハイフン区切りで指定してください。

    Returns:
        実行結果オブジェクト (ValidateDesignOutput)。
    """
    executor = SkillExecutor()
    return executor.validate_design(skill=skill)

