import os
import json
from pathlib import Path
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import client, GeminiRequest
from edd_agent_tools.evaluation.models import EvalCaseSet
from .models import GenerateTestCasesOutput


class SkillExecutor:
    """指定されたスキルのSKILL.mdおよびスクリプト実装に基づき、契約テストケースを自動生成し、EvalCaseSetフォーマットのJSONとしてファイルに書き出すスキル。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._client = client

    def generate_test_cases(self, skill_name: str, output_path: str) -> GenerateTestCasesOutput:
        """指定されたスキルのSKILL.mdおよびscriptsに基づき、契約テストケースを自動生成し、ファイルに書き出します。

        Args:
            skill_name: テストケースを生成する対象スキルの名前。
            output_path: 生成されたテストケースを書き出すファイルのパス。

        Returns:
            実行結果オブジェクト (GenerateTestCasesOutput)。
        """
        try:
            target_skill = self._skills_state.get_skill(skill_name)
            if not target_skill:
                print(f"Error: Skill '{skill_name}' not found.")
                return GenerateTestCasesOutput(success=False)

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

            prompt = f"""あなたはAIエージェントの契約駆動テスト（Contract Testing）を設計するエンジニアです。
以下のスキルの仕様書(SKILL.md)およびスクリプト実装に基づき、EvalCaseSetフォーマットに準拠した契約テストケースセットを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md_content}

【scripts/ ソースコード】
{scripts_content}

【生成要件】
1. 正常系（必須パラメータのみ、全パラメータ指定）と異常系（必須パラメータ欠落、不正な型）を含む少なくとも3つのテストケース(EvalCase)を作成してください。
2. 各テストケース(EvalCase)には以下を含めてください:
   - eval_case_id: ケースの一意のID (例: "eval_contract_001")
   - function_name: 対象スキルの主要な公開関数名
   - inputs: 関数呼び出し時に渡す引数マッピング
   - expected: 期待される結果（正常終了時は "success" または期待される戻り値キー、異常系はエラー型名）

EvalCaseSet スキーマに従って有効な JSON のみを出力してください。
"""
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EvalCaseSet
            )
            req = GeminiRequest(prompt=prompt, client=self._client)
            res = req.execute(config=config)
            
            raw_text = res.text if hasattr(res, "text") else str(res)
            data = json.loads(raw_text)

            output_file_path = Path(output_path)
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Contract test cases successfully generated and written to {output_file_path}")
            return GenerateTestCasesOutput(success=True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"An unexpected error occurred: {e}")
            return GenerateTestCasesOutput(success=False)
