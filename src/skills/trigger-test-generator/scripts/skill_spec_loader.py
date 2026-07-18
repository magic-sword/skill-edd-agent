from edd_agent_tools.skills import SkillsState

class SkillSpecLoader:
    """SKILL.md仕様書をロードする責任を持つクラス。"""

    def __init__(self, skill_name: str):
        """
        SkillSpecLoaderのコンストラクタ。

        Args:
            skill_name: ロード対象のスキル名。
        """
        state = SkillsState()
        self._skill = state.get_skill(skill_name)

    def load_skill_md(self) -> str:
        """
        指定されたスキルのSKILL.mdファイルの内容を読み込みます。

        Returns:
            SKILL.mdファイルの内容を文字列として返します。

        Raises:
            FileNotFoundError: SKILL.mdファイルが見つからない場合。
            Exception: ファイル読み込み中にその他のエラーが発生した場合。
        """
        try:
            return self._skill.load_spec()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"SKILL.mdファイルが見つかりません: {self._skill.name} - {e}")
        except Exception as e:
            raise Exception(f"SKILL.mdファイルの読み込み中にエラーが発生しました: {e}")
