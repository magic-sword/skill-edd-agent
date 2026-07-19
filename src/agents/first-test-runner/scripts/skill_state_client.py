"""
SkillsState を操作し、スキルを登録するためのクライアントモジュール。
"""

from google.adk.access import SkillsState
from google.adk.models import Skill

class SkillStateClient:
    """
    SkillsState を介してスキルを登録するクライアント。
    """
    def __init__(self, skills_state: SkillsState):
        """
        SkillStateClientのコンストラクタ。

        Args:
            skills_state: SkillsStateインスタンス。スキルの登録のために必要。
        """
        self._skills_state = skills_state

    def register_skill_as_tier1(self, skill_obj: Skill) -> None:
        """
        指定されたスキルをTier 1としてSkillsStateに登録する。

        Args:
            skill_obj: 登録対象のSkillオブジェクト。
        """
        skill_obj.set_tier(1)
        self._skills_state.register_skill(skill_obj)
