import json
from pydantic import BaseModel, Field
from typing import List
from google.genai import types
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from edd_agent_tools.evaluation.models import (
    TrajectoryEvalSet, TrajectoryEvalCase, ConversationTurn,
    IntermediateData, ToolUse, SessionInput
)

# LLMから取得するテストケースの暫定スキーマ定義
class TriggerTestCase(BaseModel):
    text: str = Field(..., description="生成されたプロンプトテキスト")

class TriggerTestCases(BaseModel):
    positive_prompts: List[TriggerTestCase] = Field(..., description="ポジティブなトリガープロンプトのリスト")
    negative_prompts: List[TriggerTestCase] = Field(..., description="ネガティブなトリガープロンプトのリスト")


class LlmEvaluator:
    """LLMを用いてSKILL.mdの仕様の明確性を評価し、テストケースを生成する責任を持つクラス。"""

    def __init__(self, skill_name: str):
        """
        LlmEvaluatorのコンストラクタ。

        Args:
            skill_name: 評価・生成対象のスキル名。
        """
        state = SkillsState()
        self._target_skill = state.get_skill(skill_name)
        self._my_skill = state.get_skill("trigger-test-generator")
        self._gemini_client = GeminiClient()
        self._skill_name = skill_name

    def _load_prompt_template(self, prompt_file_name: str) -> str:
        """
        指定されたプロンプトテンプレートファイルをロードします。
        """
        return self._my_skill.load_asset(f"prompts/{prompt_file_name}")

    def evaluate_skill_clarity(self, skill_spec_content: str) -> bool:
        """
        スキル仕様の明確性・特定性をLLMで評価します。

        Args:
            skill_spec_content: SKILL.mdファイルの内容。

        Returns:
            評価が合格であればTrue、不合格であればFalse。
        """
        prompt_template = self._load_prompt_template("evaluate_skill_spec_clarity.txt")
        prompt = prompt_template.replace("{skill_spec_content}", skill_spec_content)

        response = self._gemini_client.request(prompt).execute()
        result = response.text.strip().upper()

        return result == "OK"

    def generate_test_cases(self, skill_spec_content: str) -> TrajectoryEvalSet:
        """
        LLMを用いてインテント評価用テストケースを生成し、TrajectoryEvalSetを構築します。

        Args:
            skill_spec_content: SKILL.mdファイルの内容。

        Returns:
            構築された TrajectoryEvalSet オブジェクト。
        """
        prompt_template = self._load_prompt_template("generate_intent_test_cases.txt")
        prompt = prompt_template.replace("{skill_spec_content}", skill_spec_content)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TriggerTestCases,
            temperature=0.2
        )

        # Gemini 2.0 APIの response_schema を指定して構造化出力を得る
        response = self._gemini_client.request(prompt).execute(config=config)

        try:
            # json_str の抽出
            raw_text = response.text.strip()
            if raw_text.startswith("```json") and raw_text.endswith("```"):
                json_str = raw_text[len("```json"):-len("```")].strip()
            else:
                json_str = raw_text
            
            generated = TriggerTestCases.model_validate_json(json_str)
            
            eval_cases = []
            
            # Positiveケースの構築
            for i, item in enumerate(generated.positive_prompts):
                tool_name = self._skill_name.replace('-', '_')
                tool_uses = [
                    ToolUse(
                        name=tool_name,
                        args={
                            "params": {
                                "skill": self._skill_name,
                                "prompt": item.text
                            }
                        }
                    )
                ]
                turn = ConversationTurn(
                    invocation_id=f"inv_pos_{i+1}",
                    user_content={"role": "user", "parts": [{"text": item.text}]},
                    final_response={"role": "model", "parts": [{"text": "Dummy"}]},
                    intermediate_data=IntermediateData(tool_uses=tool_uses)
                )
                eval_cases.append(
                    TrajectoryEvalCase(
                        eval_id=f"positive_{i+1}",
                        conversation=[turn],
                        session_input=SessionInput(app_name="evaluation_driven_development_agent", user_id="user")
                    )
                )

            # Negativeケースの構築
            for i, item in enumerate(generated.negative_prompts):
                turn = ConversationTurn(
                    invocation_id=f"inv_neg_{i+1}",
                    user_content={"role": "user", "parts": [{"text": item.text}]},
                    final_response={"role": "model", "parts": [{"text": "Dummy"}]},
                    intermediate_data=IntermediateData(tool_uses=[])
                )
                eval_cases.append(
                    TrajectoryEvalCase(
                        eval_id=f"negative_{i+1}",
                        conversation=[turn],
                        session_input=SessionInput(app_name="evaluation_driven_development_agent", user_id="user")
                    )
                )

            return TrajectoryEvalSet(
                eval_set_id=f"{self._skill_name}_trigger_test_set",
                name=f"Trigger Evaluation for {self._skill_name}",
                eval_cases=eval_cases
            )

        except Exception as e:
            raise ValueError(f"テストケースの生成またはパース中にエラーが発生しました: {e}\nRaw Response: {response.text}")
