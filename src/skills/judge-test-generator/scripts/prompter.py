import json
from edd_agent_tools.skills import SkillsState

class Prompter:
    """LLMへのプロンプトを構築する責務を持つクラス。"""
    def __init__(self):
        state = SkillsState()
        self._my_skill = state.get_skill("judge-test-generator")

    def build_judge_test_prompt(
        self,
        skill_name: str,
        design_json_content: dict,
        skill_md_content: str
    ) -> str:
        """design.jsonとSKILL.mdの内容を元に、ルーブリックジャッジテスト生成用のプロンプトを構築します。

        Args:
            skill_name: ルーブリックテストを生成する対象スキルの名前。
            design_json_content: design.jsonの内容を表す辞書。
            skill_md_content: SKILL.mdの内容を表す文字列。

        Returns:
            LLMに渡すためのプロンプト文字列。
        """
        design_json_str = json.dumps(design_json_content, indent=2, ensure_ascii=False)
        prompt_template = self._my_skill.load_asset("prompts/generate_judge_cases.txt")

        return prompt_template.replace(
            "{design_json_content}", design_json_str
        ).replace(
            "{skill_md_content}", skill_md_content
        )
