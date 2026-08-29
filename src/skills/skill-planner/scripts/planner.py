#!/usr/bin/env python3
"""
要件プロンプトを分析し、最適な開発ルート（新規作成、既存更新、事前提案）と構成計画を策定するスクリプト。
Anthropic 標準および Progressive Disclosure 規約に準拠したフラットな実装。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

from edd_agent_tools import clean_pydantic_schema
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import client
from google.genai import types


class ProposedSkill(BaseModel):
    name: str = Field(..., description="提案する事前開発スキルの名前（ケバブケース推奨、例: 'log-parser'）。")
    description: str = Field(..., description="提案する事前開発スキルの具体的な役割・機能要件の説明。")


class SkillPlannerOutput(BaseModel):
    route: Literal['create_skill', 'create_workflow', 'update_skill', 'update_workflow', 'proposal'] = Field(
        ...,
        description="判定された開発ルート（'create_skill': 新規単体スキル, 'create_workflow': 新規ワークフロー, 'update_skill': 既存の単体スキル化更新, 'update_workflow': 既存のワークフロー化更新, 'proposal': 事前提案）。"
    )
    target_skill: Optional[str] = Field(
        default=None,
        description="route が 'update_skill' または 'update_workflow' の場合に特定された既存スキル/ワークフローの名前。"
    )
    rationale: str = Field(..., description="そのルートに決定した分析理由。")
    recommended_dependencies: list[str] = Field(
        default_factory=list,
        description="ワークフローの場合に推奨される既存スキル名のリスト。"
    )
    proposed_skill: Optional[ProposedSkill] = Field(
        default=None,
        description="route が 'proposal' の場合に提案される、事前に開発しておくべき単体スキルの情報。"
    )


class SkillPlanner:
    """要件プロンプトを分析し、最適な開発計画を策定するプランナーエンジン。"""

    def __init__(self):
        self._state = SkillsState()
        self._client = client
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """assets/prompts/planning_prompt.txt をロードします。"""
        current_dir = Path(__file__).resolve().parent
        template_path = current_dir.parent / "assets" / "prompts" / "planning_prompt.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def plan(self, prompt: str) -> SkillPlannerOutput:
        """要件プロンプトから開発計画を策定します。"""
        try:
            # 1. 既存スキル一覧の取得
            existing_skills = []
            for name, skill_obj in self._state.list_skills().items():
                desc = ""
                if os.path.exists(skill_obj.spec_path):
                    try:
                        spec = skill_obj.load_spec()
                        # description 抽出
                        import re
                        m = re.search(r"description:\s*([^\n]+)", spec)
                        if m:
                            desc = m.group(1).strip("\"' ")
                    except Exception:
                        pass
                existing_skills.append({
                    "name": name,
                    "description": desc or f"Skill {name}"
                })

            # 2. プロンプトの組み立て
            skills_text_list = []
            for s in existing_skills:
                skills_text_list.append(f"- スキル名: {s['name']}\n  説明: {s['description']}")
            skills_inventory_str = "\n".join(skills_text_list) if skills_text_list else "なし（既存スキルがまだ登録されていません）"

            full_prompt_text = self._prompt_template.format(
                skills_inventory=skills_inventory_str,
                requirement_prompt=prompt
            )

            # 3. Gemini API による構造化 JSON の生成
            response = self._client.generate_content(
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=full_prompt_text)]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=clean_pydantic_schema(SkillPlannerOutput),
                    temperature=0.1
                )
            )

            result_data = json.loads(response.text)
            return SkillPlannerOutput(**result_data)

        except Exception as e:
            return SkillPlannerOutput(
                route="create_skill",
                target_skill=None,
                rationale=f"Error occurred during planning: {str(e)}. Fallback to create_skill.",
                recommended_dependencies=[],
                proposed_skill=None
            )


def plan_skill_development(prompt: str) -> SkillPlannerOutput:
    """ユーザーの要件プロンプトから開発ルートと構成計画を策定します。"""
    planner = SkillPlanner()
    return planner.plan(prompt=prompt)


def main():
    parser = argparse.ArgumentParser(description="Analyze requirement prompt and plan skill development route.")
    parser.add_argument("prompt", type=str, nargs="?", default="", help="Natural language requirement prompt")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output planning JSON")
    args = parser.parse_args()

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    res = plan_skill_development(prompt=args.prompt)
    out_json = res.model_dump_json(indent=2)

    if args.output:
        Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"✅ Saved planning result to: {args.output}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()
