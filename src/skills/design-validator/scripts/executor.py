from .models import Output
from .validator import DesignValidator

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。

    Args:
        skill: 検証対象のスキル名。
    """
    def __init__(self, skill: str):
        self.skill = skill
        self._validator = DesignValidator()

    def execute(self) -> Output:
        """
        ビジネスロジックを実行し、結果を返します。

        Returns:
            処理結果の構造化データ（Output）。
        """
        return self._validator.validate_skill(skill_name=self.skill)
