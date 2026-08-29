import json
import os
from google.genai import types
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import client, GeminiRequest
from .models import JudgeCaseSet
from .prompter import Prompter

class SkillExecutor:
    """SKILL.mdおよび実装スクリプトをインプットとして、ルーブリックジャッジテストケースをLLMで自動生成しファイルに書き出すスキル。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._prompter = Prompter()
        self._client = client

    def generate_tests(self, skill_name: str, output_path: str) -> bool:
        """SKILL.mdおよびスクリプトをインプットとして、ルーブリック評価セットをLLMで自動生成して書き出します。

        Args:
            skill_name: ジャッジテストを生成する対象スキルの名前。
            output_path: 生成されたジャッジテストファイルを書き出す絶対パス。

        Returns:
            成功すれば True, 失敗すれば False。
        """
        try:
            # 1. パスの自動解決
            target_skill = self._skills_state.get_skill(skill_name)
            skill_md_path = target_skill.spec_path

            if not os.path.exists(skill_md_path):
                print(f"Error: SKILL.md not found at {skill_md_path}")
                return False

            # 2. SKILL.mdおよびスクリプト一覧を読み込む
            skill_md_content = target_skill.load_spec()
            scripts = target_skill.list_scripts()
            scripts_summary = "\n".join([f"- scripts/{s}" for s in scripts]) if scripts else "No scripts defined."

            # 3. LLMへのプロンプトを構築する
            llm_prompt = self._prompter.build_judge_test_prompt(
                skill_name=skill_name,
                skill_md_content=skill_md_content,
                scripts_summary=scripts_summary
            )

            # 4. Gemini API の response_schema を指定して構造化出力を得る
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JudgeCaseSet,
                temperature=0.2
            )
            req = GeminiRequest(prompt=llm_prompt, client=self._client)
            response = req.execute(config=config)

            # json_str の抽出
            raw_text = response.text.strip()
            if raw_text.startswith("```json") and raw_text.endswith("```"):
                json_str = raw_text[len("```json"):-len("```")].strip()
            else:
                json_str = raw_text

            # バリデーション
            generated = JudgeCaseSet.model_validate_json(json_str)

            # 5. 生成されたジャッジテストデータをファイルに書き出す
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(generated.model_dump_json(indent=2))

            print(f"🎉 Judge test cases successfully generated and written to {output_path}")
            return True

        except Exception as e:
            print(f"Error generating judge test cases: {e}")
            return False
