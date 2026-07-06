import json
from google.genai import types
from edd_agent_tools import GeminiClient
from .schemas import StaticEvalResult

class StaticEvaluator:
    """SKILL.mdの静的評価を行うクラス。"""

    def __init__(self):
        """StaticEvaluator を初期化します。"""
        # パッケージ初期ロード時の循環参照を回避するため、実行時に遅延ローカルインポート
        from edd_agent_tools.registry import SkillRegistry

        self.genai_client = GeminiClient()
        self_dir = SkillRegistry().get_skill(name="trigger-evaluator")
        self.static_prompt_template = self_dir.load_asset("static_eval_prompt.txt")
        
        eval_criteria_str = self_dir.load_asset("eval_criteria.json")
        self.eval_criteria = json.loads(eval_criteria_str)

    def evaluate(self, skill_name: str, skill_md_content: str) -> dict:
        """SKILL.mdの静的評価（具体性、明確性）を実行します。

        Args:
            skill_name: 評価対象のスキル名。
            skill_md_content: 評価対象のSKILL.mdの内容。

        Returns:
            dict: 具体性、明確性、合格/不合格、フィードバックを含む評価結果の辞書。
        """
        print(f"[第1ゲート] スキル '{skill_name}' のSKILL.mdを静的評価中...\n")

        prompt = self.static_prompt_template.replace(
            "{eval_criteria}", json.dumps(self.eval_criteria, indent=2, ensure_ascii=False)
        ).replace(
            "{skill_md_content}", skill_md_content
        )

        try:
            response = self.genai_client.generate_content(
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StaticEvalResult,
                    temperature=0.1
                )
            )
            eval_result_pydantic = StaticEvalResult.model_validate_json(response.text)
            specificity = eval_result_pydantic.specificity
            clarity = eval_result_pydantic.clarity
            feedback = eval_result_pydantic.feedback

            print(f"  - 具体性 (Specificity): {specificity}/5")
            print(f"  - 明確性 (Clarity): {clarity}/5")
            print(f"  - フィードバック: {feedback}")

            if specificity >= 4 and clarity >= 4:
                print("  => 静的評価: 合格 (Specificity >= 4, Clarity >= 4)\n")
                return {"specificity": specificity, "clarity": clarity, "passed": True, "feedback": feedback}
            else:
                print("  => 静的評価: 不合格 (Specificity < 4 または Clarity < 4)\n")
                return {"specificity": specificity, "clarity": clarity, "passed": False, "feedback": feedback}
        except Exception as e:
            print(f"  => 静的評価中にエラーが発生しました: {e}\n")
            return {"specificity": 0, "clarity": 0, "passed": False, "error": str(e), "feedback": "評価中にエラーが発生しました。"}
