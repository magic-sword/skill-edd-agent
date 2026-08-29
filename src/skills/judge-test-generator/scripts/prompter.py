from edd_agent_tools.skills import SkillsState

class Prompter:
    """LLMへのプロンプトを構築する責務を持つクラス。"""
    def __init__(self):
        state = SkillsState()
        self._my_skill = state.get_skill("judge-test-generator")

    def build_judge_test_prompt(
        self,
        skill_name: str,
        skill_md_content: str,
        scripts_summary: str = ""
    ) -> str:
        """SKILL.mdと実装スクリプトの内容を元に、ルーブリックジャッジテスト生成用のプロンプトを構築します。

        Args:
            skill_name: ジャッジテストを生成する対象スキルの名前。
            skill_md_content: SKILL.mdの内容を表す文字列。
            scripts_summary: スクリプト一覧および概要。

        Returns:
            LLMに渡すためのプロンプト文字列。
        """
        prompt_template = self._my_skill.load_asset("prompts/generate_judge_cases.txt")

        return prompt_template.replace(
            "{skill_md_content}", skill_md_content
        ).replace(
            "{scripts_summary}", scripts_summary
        )
