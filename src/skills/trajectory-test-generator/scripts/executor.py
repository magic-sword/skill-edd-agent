import os
import json
from google.genai import types
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from edd_agent_tools.evaluation.models import TrajectoryEvalSet

class TrajectoryTestGenerator:
    """指定されたスキルの仕様（SKILL.md や design.json）から TrajectoryEvalSet を生成・保存するクラス。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._gemini_client = GeminiClient()

    def generate_tests(self, skill_name: str, output_path: str) -> bool:
        """指定されたスキルの仕様から軌跡評価用テストケースを生成し、JSONとして保存します。

        Args:
            skill_name: テスト対象のスキル名。
            output_path: 保存先のファイルパス。

        Returns:
            成功時は True、失敗時は False。
        """
        try:
            target_skill = self._skills_state.get_skill(skill_name)
            design_path = target_skill.design_path
            spec_path = target_skill.spec_path

            design_content = "{}"
            if design_path and os.path.exists(design_path):
                with open(design_path, "r", encoding="utf-8") as f:
                    design_content = f.read()

            skill_md_content = ""
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r", encoding="utf-8") as f:
                    skill_md_content = f.read()

            prompt = f"""あなたはAIエージェントの評価テストを設計するスペシャリストです。
以下のスキルの設計定義(design.json)および仕様書(SKILL.md)に基づき、Google ADKの軌跡評価フォーマット(TrajectoryEvalSet)に準拠したテストケースセットを生成してください。

【対象スキル名】
{skill_name}

【design.json】
{design_content}

【SKILL.md】
{skill_md_content}

【生成要件】
1. 正常系(通常シナリオ)と境界/注意ケースを含め、少なくとも3つの評価ケース(TrajectoryEvalCase)を作成してください。
2. 各テストケース(TrajectoryEvalCase)には以下を含めてください:
   - eval_id: ケースの一意のID (例: "eval_traj_001")
   - session_input: app_name="test-app", user_id="user-001"
   - conversation: ターンリスト(ConversationTurn)。各ターンには以下を含める:
     - invocation_id: "inv_001" 等
     - user_content: {{"text": "ユーザーの要求文"}}
     - final_response: {{"text": "期待されるモデルの最終応答概要"}}
     - intermediate_data: {{"tool_uses": [{{"name": "呼び出されるツール/関数名", "args": {{"引数名": "引数値"}}}}]}}
3. ユーザーの要求プロンプト(user_content)に対して、対象スキル(またはその中の関数)が期待されるツール名と引数で呼び出されるような具体的な軌跡データを生成してください。
"""

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TrajectoryEvalSet,
                temperature=0.2
            )

            response = self._gemini_client.request(prompt).execute(config=config)
            raw_text = response.text.strip()

            if raw_text.startswith("```json") and raw_text.endswith("```"):
                json_str = raw_text[len("```json"):-len("```")].strip()
            else:
                json_str = raw_text

            # バリデーションチェック
            eval_set = TrajectoryEvalSet.model_validate_json(json_str)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(eval_set.model_dump_json(indent=2))

            print(f"[TrajectoryTestGenerator] Successfully generated trajectory eval set to {output_path}")
            return True

        except Exception as e:
            print(f"[TrajectoryTestGenerator] Error generating tests: {e}")
            import traceback
            traceback.print_exc()
            return False
