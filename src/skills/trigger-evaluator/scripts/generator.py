from typing import List
from google.genai import types
from edd_agent_tools import GeminiClient
from .schemas import TriggerTestCases, EvalCase

class TriggerGenerator:
    """トリガー評価用のテストケースを自動生成するクラス。"""

    def __init__(self):
        """TriggerGenerator を初期化します。"""
        # パッケージ初期ロード時の循環参照を回避するため、実行時に遅延ローカルインポート
        from edd_agent_tools.registry import SkillRegistry

        self.genai_client = GeminiClient()
        self_dir = SkillRegistry().get_skill(name="trigger-evaluator")
        self.test_gen_prompt_template = self_dir.load_asset("test_case_gen_prompt.txt")

    def generate(self, skill_name: str, skill_md_content: str) -> List[EvalCase]:
        """トリガー評価用のテストケースを自動生成します。

        Args:
            skill_name: テストケース生成対象のスキル名。
            skill_md_content: テストケース生成の基となるSKILL.mdの内容。

        Returns:
            List[EvalCase]: 生成された評価ケースモデルオブジェクトのリスト。
        """
        print(f"[第2ゲート] スキル '{skill_name}' のトリガー評価用テストケースを生成中...\n")

        prompt = self.test_gen_prompt_template.replace(
            "{skill}", skill_name
        ).replace(
            "{skill_md_content}", skill_md_content
        )

        try:
            response = self.genai_client.generate_content(
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TriggerTestCases,
                    temperature=0.2
                )
            )
            generated_cases_pydantic = TriggerTestCases.model_validate_json(response.text)

            eval_cases = []
            
            # OOP: 辞書の手動組み立てを完全排除し、スキーマモデルの自己マッピングへ移行
            for i, item in enumerate(generated_cases_pydantic.positive_prompts):
                eval_cases.append(item.to_eval_case(skill_name=skill_name, index=i, is_positive=True))

            for i, item in enumerate(generated_cases_pydantic.negative_prompts):
                eval_cases.append(item.to_eval_case(skill_name=skill_name, index=i, is_positive=False))

            return eval_cases
        except Exception as e:
            print(f"  => テストケース生成中にエラーが発生しました: {e}\n")
            return []
