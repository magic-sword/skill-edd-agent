"""
Trace Harvester (Authoring from Traces)

ホワイトペーパー Section 6 (p.36-37, Point 2, Fig 9) 準拠：
エージェントの会話履歴やツール実行軌跡（Traces）から再利用可能なワークフローを抽出し、
新しい SKILL.md およびリソース雛形（scripts, tests）を自律生成するハーベスター。
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from edd_agent_tools.models.spec import SkillFrontmatter
from edd_agent_tools.packaging.scaffold import SkillScaffolder


class TraceHarvester:
    """エージェントの実行軌跡（Traces）からスキルを自動抽出・生成するクラス。"""

    def harvest_skill_from_trace(
        self,
        trace_data: Dict[str, Any] | List[Dict[str, Any]],
        suggested_skill_name: str,
        output_base_dir: Optional[str | Path] = None,
        pattern: str = "task_based"
    ) -> Dict[str, Any]:
        """会話・ツール実行トレースからスキルドラフトを生成します。

        Args:
            trace_data: ADK Trace または 会話セッション辞書/リスト。
            suggested_skill_name: 生成するスキルの論理名（kebab-case）。
            output_base_dir: 出力先ディレクトリ（デフォルト: src/skills）。
            pattern: スキルパターン（task_based, workflow 等）。

        Returns:
            Dict[str, Any]: 生成されたスキル情報と抽出されたステップ。
        """
        # トレースからステップと使用ツールを抽出
        steps, tools_used, user_intent = self._extract_workflow_from_trace(trace_data)

        # スキャフォールドによるディレクトリ生成
        base_dir = output_base_dir or Path("src/skills")
        skill_dir = SkillScaffolder.scaffold(
            skill_name=suggested_skill_name,
            output_base_dir=base_dir,
            pattern=pattern
        )

        # 抽出されたステップとユーザー意図を SKILL.md に反映
        spec_path = skill_dir / "SKILL.md"
        if spec_path.exists():
            content = spec_path.read_text(encoding="utf-8")
            
            # 手順セクションの更新
            workflow_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)]) if steps else "1. Execute task instructions.\n2. Verify output."
            
            if "## Workflow" in content:
                content = re.sub(r"## Workflow\n[\s\S]*?(?=\n##|\Z)", f"## Workflow\n{workflow_text}\n", content)
            
            # Description の更新
            desc_text = f"Automates {user_intent or suggested_skill_name}. Use this skill when the user asks to {user_intent or 'perform this task'}."
            content = re.sub(r"(description:\s*\|?\s*\n?)(?:[ \t]+[^\n]+\n*)+", f"description: |\n  {desc_text}\n", content)
            
            spec_path.write_text(content, encoding="utf-8")

        # トレースから Google ADK 2.0 公式 EvalSet 形式の初期評価データセットを生成
        tests_dir = skill_dir / "tests"
        if tests_dir.exists():
            edd_file = tests_dir / f"{suggested_skill_name}_edd.evalset.json"
            cid = f"{suggested_skill_name.replace('-', '_')}_harvested_001"
            main_script = f"scripts/{suggested_skill_name.replace('-', '_')}.py"
            inp_text = user_intent or f"Execute {suggested_skill_name} workflow"

            eval_cases = [
                {
                    "eval_id": cid,
                    "case_id": cid,
                    "expected_skill": suggested_skill_name,
                    "conversation": [
                        {
                            "invocation_id": f"inv_{cid}",
                            "user_content": {"role": "user", "parts": [{"text": inp_text}]},
                            "final_response": {"role": "model", "parts": [{"text": "status_confirmation"}]},
                            "intermediate_data": {
                                "tool_uses": [
                                    {
                                        "name": "run_skill_script",
                                        "args": {
                                            "skill_name": suggested_skill_name,
                                            "file_path": main_script,
                                            "args": ["--help"]
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "rubrics": [
                        {
                            "rubric_id": f"r_{cid}_1",
                            "rubric_content": {"text_property": f"correctly invokes run_skill_script with {main_script}"},
                            "type": "TOOL_USE_QUALITY"
                        },
                        {
                            "rubric_id": f"r_{cid}_2",
                            "rubric_content": {"text_property": "completes harvested workflow"},
                            "type": "FINAL_RESPONSE_QUALITY"
                        }
                    ]
                }
            ]

            eval_case_data = {
                "eval_set_id": f"{suggested_skill_name}_edd",
                "name": f"{suggested_skill_name}_edd",
                "description": f"Harvested Google ADK 2.0 EvalSet for {suggested_skill_name}",
                "skill_name": suggested_skill_name,
                "eval_cases": eval_cases,
                "cases": eval_cases
            }
            with open(edd_file, "w", encoding="utf-8") as f:
                json.dump(eval_case_data, f, ensure_ascii=False, indent=2)


        return {
            "status": "harvested",
            "skill_name": suggested_skill_name,
            "skill_dir": str(skill_dir),
            "extracted_steps": steps,
            "tools_used": tools_used,
            "user_intent": user_intent,
            "message": f"Successfully harvested draft skill '{suggested_skill_name}' from execution trace."
        }

    def _extract_workflow_from_trace(
        self,
        trace_data: Dict[str, Any] | List[Dict[str, Any]]
    ) -> tuple[List[str], List[str], str]:
        """トレースデータ構造をパースしてワークフローステップを抽出。"""
        steps: List[str] = []
        tools: List[str] = []
        user_intent = ""

        events = []
        if isinstance(trace_data, dict):
            events = trace_data.get("events") or trace_data.get("conversation") or [trace_data]
            user_intent = trace_data.get("initial_prompt") or trace_data.get("user_query", "")
        elif isinstance(trace_data, list):
            events = trace_data

        for event in events:
            if not isinstance(event, dict):
                continue

            # ユーザー発話
            if event.get("role") == "user" or "user_content" in event:
                u_text = event.get("content") or event.get("user_content", {}).get("parts", [{}])[0].get("text", "")
                if u_text and not user_intent:
                    user_intent = u_text

            # ツール呼び出し
            tool_uses = event.get("tool_uses") or event.get("intermediate_data", {}).get("tool_uses", [])
            for tu in tool_uses:
                t_name = tu.get("name") if isinstance(tu, dict) else str(tu)
                if t_name:
                    tools.append(t_name)
                    steps.append(f"Call tool '{t_name}' with verified arguments.")

            # アクション・テキスト
            if event.get("action"):
                steps.append(str(event.get("action")))

        if not steps:
            steps = ["Parse input parameters.", "Execute domain processing.", "Format and return structured response."]

        return steps, tools, user_intent
