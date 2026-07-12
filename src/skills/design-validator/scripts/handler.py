from .models import Output
from .executor import SkillExecutor

def validate_design(skill: str) -> dict:
    """指定されたスキルの設計仕様（design.json）と生成されたソースコードを読み込み、Gemini API を用いて仕様と実装の整合性を検証します。

    Args:
        skill: 検証対象のスキル名。

    Returns:
        検証結果（status, details, score）を含む辞書。
    """
    executor = SkillExecutor(skill=skill)
    result = executor.execute()
    return result.model_dump()
