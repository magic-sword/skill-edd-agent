import os
import json
from google.genai import types
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import client, GeminiRequest
from edd_agent_tools.evaluation.models import TrajectoryEvalSet


class TrajectoryTestGenerator:
    """指定されたスキルの仕様（SKILL.md や scripts/）から TrajectoryEvalSet を生成・保存するクラス。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._client = client

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
            if not target_skill:
                print(f"スキル '{skill_name}' が見つかりません。")
                return False

            spec_path = target_skill.spec_path
            skill_md_content = ""
            if spec_path and os.path.exists(spec_path):
                with open(spec_path, "r", encoding="utf-8") as f:
                    skill_md_content = f.read()

            scripts_summary = []
            if os.path.isdir(target_skill.scripts_dir):
                for py_file in os.listdir(target_skill.scripts_dir):
                    if py_file.endswith(".py"):
                        p = os.path.join(target_skill.scripts_dir, py_file)
                        with open(p, "r", encoding="utf-8") as f:
                            scripts_summary.append(f"### {py_file}\n```python\n{f.read()}\n```")
            scripts_content = "\n\n".join(scripts_summary)

            prompt = f"""あなたはAIエージェントの評価テストを設計するスペシャリストです。
以下のスキルの仕様書(SKILL.md)およびスクリプト実装に基づき、Google ADKの軌跡評価フォーマット(TrajectoryEvalSet)に準拠したテストケースセットを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md_content}

【scripts/ ソースコード】
{scripts_content}

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

TrajectoryEvalSet スキーマに従って有効な JSON のみを出力してください。
"""
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TrajectoryEvalSet
            )
            req = GeminiRequest(prompt=prompt, client=self._client)
            res = req.execute(config=config)
            
            raw_text = res.text if hasattr(res, "text") else str(res)
            data = json.loads(raw_text)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"TrajectoryEvalSet generated successfully at: {output_path}")
            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to generate trajectory tests: {e}")
            return False
