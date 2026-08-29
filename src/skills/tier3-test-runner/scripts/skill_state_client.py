"""
SkillsState を操作し、スキルをTier 3登録するためのクライアントモジュール。
"""

from edd_agent_tools.skills import SkillsState, Skill, SkillTier

class SkillStateClient:
    """
    SkillsState を介してスキルをTier 3として登録するクライアント。
    """
    def __init__(self, skills_state: SkillsState):
        """
        SkillStateClientのコンストラクタ。

        Args:
            skills_state: SkillsStateインスタンス。
        """
        self._skills_state = skills_state

    def register_skill_as_tier3(self, skill_obj: Skill) -> None:
        """
        指定されたスキルをTier 3 (ACTION_ALLOWED) としてSkillsStateに登録します。
        """
        # 最新情報をスキャン
        self._skills_state.scan_skills(force_reload=True)
        
        # すでに Tier 3 の場合はスキップ
        if skill_obj._tier >= 3:
            print(f"INFO: Skill '{skill_obj.name}' is already registered as Tier {SkillTier(skill_obj._tier).name}. Skipping.")
            return

        skill_obj.set_tier(3) # ACTION_ALLOWED
        registered = self._skills_state.register_skill(skill_obj)
        if not registered:
            raise RuntimeError(f"SkillsState.register_skill が False を返しました（Tier 3 登録失敗）。")
