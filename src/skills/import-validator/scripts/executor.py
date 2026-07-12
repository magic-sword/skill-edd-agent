from .models import Output

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。

    Args:
        skill: ロードを試みる対象のスキル名。
    """
    def __init__(self, skill: str):
        self.skill = skill

    def execute(self) -> Output:
        """ビジネスロジックを実行し、結果を返します。

        Returns:
            処理結果の構造化データ（Output）。

        Raises:
            NotImplementedError: ロジックが未実装の場合。
        """
        from .client import SkillsStateClient
        from .skill_validator import SkillValidator

        # 1. SkillsStateClientのインスタンスを作成
        skills_state_client = SkillsStateClient()

        # 2. SkillValidatorのインスタンスを作成し、クライアントを渡す
        skill_validator = SkillValidator(skills_state_client)

        # 3. スキルの動的ロード検証を実行
        status, details = skill_validator.validate_skill_import(self.skill)

        # 4. 結果をOutputモデルにマッピングして返却
        score = 1.0 if status == 'success' else 0.0
        return Output(status=status, details=details, score=score)
