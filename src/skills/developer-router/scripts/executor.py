import json
import sys
from edd_agent_tools import clean_pydantic_schema
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import client
from google.genai import types

from .models import DeveloperRouterOutput
from .prompter import build_routing_prompt

class DeveloperRouterExecutor:
    """
    要件プロンプトを分析し、単体スキルかワークフローかを分類してルーティングする
    ビジネスロジックエグゼキューター。
    """
    def __init__(self):
        self._state = SkillsState()
        self._client = client

    def route_requirement(self, prompt: str) -> DeveloperRouterOutput:
        try:
            # 1. 既存スキル一覧の取得
            self._state.load()
            existing_skills = []
            for skill_obj in self._state.list_skills():
                try:
                    design = skill_obj.load_design()
                    existing_skills.append({
                        "name": design.name,
                        "description": design.description
                    })
                except Exception as e:
                    skill_name = getattr(skill_obj, "name", "unknown")
                    print(f"警告: スキル {skill_name} のロード中にエラーが発生しました: {e}", file=sys.stderr)

            # 2. プロンプトの組み立て
            contents = build_routing_prompt(prompt, existing_skills)

            # 3. Gemini API による構造化 JSON の生成
            print("Gemini API を呼び出して要件を分析中...")
            response = self._client.generate_content(
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=clean_pydantic_schema(DeveloperRouterOutput),
                    temperature=0.1
                )
            )

            # 4. レスポンスのパースと返却
            result_data = json.loads(response.text)
            return DeveloperRouterOutput(**result_data)

        except Exception as e:
            print(f"❌ ルーティング判定中に致命的なエラーが発生しました: {e}", file=sys.stderr)
            return DeveloperRouterOutput(
                route="skill",
                rationale=f"Error occurred during routing: {str(e)}. Fallback to atomic skill development.",
                recommended_dependencies=[]
            )
