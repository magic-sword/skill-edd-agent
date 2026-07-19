"""
SkillsState を操作し、スキルをTier 1登録するためのクライアントモジュール。
"""

from edd_agent_tools.skills import SkillsState, Skill, SkillTier

class SkillStateClient:
    """
    SkillsState を介してスキルを登録するクライアント。
    """
    def __init__(self, skills_state: SkillsState):
        """
        SkillStateClientのコンストラクタ。

        Args:
            skills_state: SkillsStateインスタンス。
        """
        self._skills_state = skills_state

    def register_skill_as_tier1(self, skill_obj: Skill) -> None:
        """
        指定されたスキルをTier 1 (READ_ONLY) としてSkillsStateに登録します。
        すでに登録済みの場合は処理をスキップします。
        """
        # 最新情報をスキャン
        self._skills_state.scan_skills(force_reload=True)
        
        # 二重登録回避
        if skill_obj._tier >= 1:
            print(f"INFO: Skill '{skill_obj.name}' is already registered as Tier {SkillTier(skill_obj._tier).name}. Skipping.")
            return

        skill_obj.set_tier(1) # READ_ONLY
        registered = self._skills_state.register_skill(skill_obj)
        if not registered:
            raise RuntimeError(f"SkillsState.register_skill が False を返しました（登録失敗）。")
