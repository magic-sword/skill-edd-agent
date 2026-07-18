from .models import ValidateDesignOutput
from .validator import DesignValidator

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。"""

    def __init__(self):
        self._validator = DesignValidator()

    def validate_design(self, skill: str) -> ValidateDesignOutput:
        """
        設計仕様と実装の整合性を検証します。

        Args:
            skill: 検証対象のスキル名。

        Returns:
            ValidateDesignOutput: 実行結果オブジェクト。
        """
        return self._validator.validate_skill(skill=skill)