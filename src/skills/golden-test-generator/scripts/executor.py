import json
import os
from google.genai import types
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from .models import GoldenCaseSet
from .prompter import Prompter

class SkillExecutor:
    """design.jsonおよびSKILL.mdをインプットとして、ゴールデンテストケースをLLMで自動生成しファイルに書き出すスキル。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._prompter = Prompter()
        self._gemini_client = GeminiClient()

    def generate_tests(self, skill_name: str, output_path: str) -> bool:
        """design.jsonおよびSKILL.mdをインプットとして、多様なユースケース入力値と、期待される正解のペアをLLMで自動生成して書き出します。

        Args:
            skill_name: ゴールデンテストを生成する対象スキルの名前。
            output_path: 生成されたゴールデンテストファイルを書き出す絶対パス。

        Returns:
            成功すれば True, 失敗すれば False。
        """
        try:
            # 1. パスの自動解決
            target_skill = self._skills_state.get_skill(skill_name)
            design_json_path = target_skill.design_path
            skill_md_path = target_skill.spec_path

            if not os.path.exists(design_json_path):
                print(f"Error: design.json not found at {design_json_path}")
                return False
            if not os.path.exists(skill_md_path):
                print(f"Error: SKILL.md not found at {skill_md_path}")
                return False

            # 2. design.jsonとSKILL.mdを読み込む
            with open(design_json_path, "r", encoding="utf-8") as f:
                design_json_content = json.load(f)
            with open(skill_md_path, "r", encoding="utf-8") as f:
                skill_md_content = f.read()

            # 3. LLMへのプロンプトを構築する
            llm_prompt = self._prompter.build_golden_test_prompt(
                skill_name=skill_name,
                design_json_content=design_json_content,
                skill_md_content=skill_md_content
            )

            # 4. Gemini 2.0 APIの response_schema を指定して構造化出力を得る
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GoldenCaseSet,
                temperature=0.2
            )
            response = self._gemini_client.request(llm_prompt).execute(config=config)

            # json_str の抽出
            raw_text = response.text.strip()
            if raw_text.startswith("```json") and raw_text.endswith("```"):
                json_str = raw_text[len("```json"):-len("```")].strip()
            else:
                json_str = raw_text

            # バリデーション
            generated = GoldenCaseSet.model_validate_json(json_str)

            # design.json に eval_scenarios が定義されている場合、決定論的ケースとしてマージ/反映
            if "eval_scenarios" in design_json_content and isinstance(design_json_content["eval_scenarios"], list):
                from .models import GoldenCase, InputParameter, ExpectedToolUse
                for idx, scenario in enumerate(design_json_content["eval_scenarios"]):
                    scen_id = scenario.get("scenario_id", f"scenario_{idx+1}")
                    scen_desc = scenario.get("description", "デザイン仕様で定義された代表シナリオ")
                    scen_input = scenario.get("input", {})
                    scen_traj = scenario.get("expected_trajectory", [])

                    inputs_list = [
                        InputParameter(name=k, value=str(v))
                        for k, v in scen_input.items()
                    ]
                    traj_list = [
                        ExpectedToolUse(name=t.get("name", ""), args=t.get("args", {}))
                        for t in scen_traj if isinstance(t, dict) and t.get("name")
                    ]

                    deterministic_case = GoldenCase(
                        eval_case_id=scen_id,
                        function_name=skill_name.replace("-", "_"),
                        inputs=inputs_list,
                        expected_response_rubric=scen_desc,
                        expected_trajectory=traj_list
                    )
                    # 重複しないように追加
                    if not any(c.eval_case_id == scen_id for c in generated.eval_cases):
                        generated.eval_cases.insert(0, deterministic_case)

            # 5. 生成されたゴールデンテストデータをファイルに書き出す
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(generated.model_dump_json(indent=2))

            print(f"🎉 Golden test cases successfully generated and written to {output_path}")
            return True

        except Exception as e:
            print(f"Error generating golden test cases: {e}")
            return False
