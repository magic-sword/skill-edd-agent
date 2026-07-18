from .models import ValidateSkillImportOutput
from .executor import SkillExecutor

def validate_skill_import(skill: str) -> ValidateSkillImportOutput:
    """指定されたスキルモジュールのインポート適合性を検証します。

    Args:
        skill: 検証対象のスキル名（例: 'my-awesome-skill'）。

    Returns:
        実行結果オブジェクト (ValidateSkillImportOutput)。
    """
    executor = SkillExecutor()
    return executor.validate_skill_import(skill=skill)

