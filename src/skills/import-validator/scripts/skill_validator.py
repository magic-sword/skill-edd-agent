
from .client import SkillsStateClient

class SkillValidator:
    """スキルの動的ロード検証ロジックを提供するクラス。"""

    def __init__(self, skills_state_client: SkillsStateClient):
        """
        SkillValidatorのコンストラクタ。

        Args:
            skills_state_client: SkillsStateメカニズムを操作するためのクライアント。
        """
        self._skills_state_client = skills_state_client

    def validate_skill_import(self, skill_name: str) -> tuple[str, str]:
        """
        指定されたスキル名の動的ロードを検証します。

        Args:
            skill_name: 動的インポートを検証する対象のスキル名。

        Returns:
            スキルの動的ロードの成否 ('success' または 'failed') と、
            失敗した場合のエラー詳細（トレースバックなど）。
        """
        is_success, details = self._skills_state_client.load_skill_module(skill_name)
        if is_success:
            return 'success', ''
        else:
            return 'failed', details

