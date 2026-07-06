import traceback
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

class SkillsStateClient:
    """ADKのSkillsStateメカニズムを操作するためのクライアント。"""

    def __init__(self, tool_context: ToolContext):
        """
        SkillsStateClientのコンストラクタ。

        Args:
            tool_context: ADKのセッション状態などを管理するコンテキスト。
        """
        self._tool_context = tool_context

    def load_skill_module(self, skill_name: str) -> tuple[bool, str]:
        """
        指定されたスキルモジュールを動的にロードします。

        Args:
            skill_name: ロードを試みる対象のスキル名。

        Returns:
            スキルロードの成否を示すブール値と、失敗した場合のトレースバック文字列。
            成功時は (True, '') を、失敗時は (False, traceback_string) を返します。
        """
        try:
            # SkillsStateを介してSkillオブジェクトを取得し、動的ロードを実行
            state = SkillsState()
            skill_obj = state.get_skill(skill_name)
            skill_obj.load_module()
            return True, ""
        except Exception:
            # ロード失敗時はトレースバックを取得
            return False, traceback.format_exc()

