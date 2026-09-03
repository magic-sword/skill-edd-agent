"""
Skill Scaffolding Utility for edd-agent-tools

Anthropic Claude Skills / Google ADK 2.0 準拠のスキルディレクトリ雛形を高速生成します。
パッケージ同梱の標準テンプレート（templates/）をデフォルトSSOTとし、外部パス依存のない自己完結設計。
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..validation.validator import SkillValidator


MINIMAL_SKILL_TEMPLATE = """---
name: {skill_name}
description: |
  Performs {skill_name_spaced} tasks and workflows.
  Use when the user asks to execute {skill_name_spaced}, process relevant inputs, or automate this domain workflow.
  Do NOT use for simple one-off commands or unrelated administrative tasks.
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: {pattern}
---

# {skill_title}

## When to use
- Please execute {skill_name_spaced} on target data
- Run the {skill_name} workflow

## When NOT to use
- Simple one-liner operations that do not require structured workflows
- Tasks outside the defined domain boundaries

## Workflow
1. Reconnaissance and Argument Inspection: To inspect incoming parameters and verify inputs before execution:
   ```bash
   python scripts/{primary_script}.py --help
   ```
2. Core Execution: To execute the task deterministically:
   ```bash
   python scripts/{primary_script}.py --input "<data>"
   ```
3. Result Verification: To verify the output matches requirements and return the formatted result.

## Examples
- Input: "Execute {skill_name} on sample" → Output: "Successfully processed sample"

## Output format
- Return direct operational summary and structured result files.

## Anti-patterns to avoid
- Do not read large scripts into LLM context window without running `--help` first.
- Do not make invalid actions; use deterministic scripts in `scripts/` for heavy lifting.

## Requirements & Prerequisites
- Python: >= 3.10

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- `scripts/{primary_script}.py`: Core CLI tool for {skill_title}.

### `references/` (On-Demand Knowledge)
- `references/guide.md`: Detailed reference specifications and edge cases.
"""



class SkillScaffolder:
    """スキルディレクトリの初期スキャフォールドを行うクラス。"""

    @classmethod
    def scaffold(
        cls,
        skill_name: str,
        output_base_dir: str | Path = "src/skills",
        pattern: str = "workflow",
        templates_dir: Optional[str | Path] = None
    ) -> Path:
        """
        指定された名前とパターンでスキルディレクトリ雛形をスキャフォールドします。
        """
        canonical_skill_name = skill_name.replace("_", "-")
        canonical_dir_name = canonical_skill_name
        primary_script = skill_name.replace("-", "_")

        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", canonical_skill_name):
            raise ValueError(f"Skill name '{skill_name}' must be lowercase alphanumeric with hyphens/underscores (e.g. pdf-tools)")

        # Google ADK 2.0 の load_skill_from_dir は skill_dir.name == frontmatter.name を必須要求するため、
        # ディレクトリ名は canonical_skill_name (kebab-case) を完全一致で配置します。
        target_dir = Path(output_base_dir).resolve() / canonical_skill_name
        if target_dir.exists():
            raise FileExistsError(f"Target skill directory already exists: {target_dir}")


        target_dir.mkdir(parents=True, exist_ok=False)
        (target_dir / "scripts").mkdir(exist_ok=True)
        (target_dir / "references").mkdir(exist_ok=True)
        (target_dir / "assets").mkdir(exist_ok=True)
        (target_dir / "examples").mkdir(exist_ok=True)
        (target_dir / "tests").mkdir(exist_ok=True)
        (target_dir / "tests" / "results").mkdir(exist_ok=True)

        skill_title = canonical_skill_name.replace("-", " ").title()
        skill_name_spaced = canonical_skill_name.replace("-", " ")
        primary_script = canonical_skill_name.replace("-", "_")


        # 1. テンプレートの探索と読み込み（Cascading Template Resolver）
        # 解決優先順位: 1. 明示指定 (templates_dir) -> 2. ワークスペース内 skill_creator/assets/templates -> 3. パッケージ組み込み templates/
        template_content = None
        cand_dirs = []
        if templates_dir:
            cand_dirs.append(Path(templates_dir).resolve())

        # ワークスペース内スキル資産層のテンプレート（自己進化プロンプト資産）
        base_path = Path(output_base_dir).resolve()
        for creator_dir_name in ["skill_creator", "skill-creator"]:
            if (base_path / creator_dir_name / "assets" / "templates").exists():
                cand_dirs.append(base_path / creator_dir_name / "assets" / "templates")
            elif (base_path.parent / "skills" / creator_dir_name / "assets" / "templates").exists():
                cand_dirs.append(base_path.parent / "skills" / creator_dir_name / "assets" / "templates")

        # パッケージ同梱の標準フォールバック・テンプレートディレクトリ
        builtin_templates_dir = Path(__file__).parent / "templates"
        if builtin_templates_dir.exists():
            cand_dirs.append(builtin_templates_dir)

        for c_dir in cand_dirs:
            t_path = c_dir / f"{pattern}_template.md"
            if t_path.exists():
                try:
                    template_content = t_path.read_text(encoding="utf-8")
                    break
                except Exception:
                    pass

        if not template_content:
            template_content = MINIMAL_SKILL_TEMPLATE

        # プレースホルダ置換
        rendered_md = template_content.replace("{skill_name}", canonical_skill_name)
        rendered_md = rendered_md.replace("{skill_title}", skill_title)
        rendered_md = rendered_md.replace("{skill_name_spaced}", skill_name_spaced)
        rendered_md = rendered_md.replace("{primary_script}", primary_script)
        rendered_md = rendered_md.replace("{pattern}", pattern)

        (target_dir / "SKILL.md").write_text(rendered_md, encoding="utf-8")

        # 2. 初期スクリプト（CLI対応・--help対応）の配置
        sample_script = target_dir / "scripts" / f"{primary_script}.py"
        script_code = f'''#!/usr/bin/env python3
"""
{skill_title} - Core CLI Tool
"""

import sys
import argparse


def run(input_val: str | None = None) -> str:
    """Core task execution."""
    print(f"Executing {canonical_skill_name} with input: {{input_val}}")
    return "Success"


def main():
    parser = argparse.ArgumentParser(description="{skill_title} execution script.")
    parser.add_argument("--input", "-i", type=str, help="Input argument or file path")
    args = parser.parse_args()

    run(args.input)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
        sample_script.write_text(script_code, encoding="utf-8")
        try:
            sample_script.chmod(0o755)
        except Exception:
            pass

        # 3. リファレンス・アセット・使用例の配置
        (target_dir / "references" / "guide.md").write_text(
            f"# Reference Guide for {skill_title}\n\nDetailed specifications and reference material for {canonical_skill_name}.\n",
            encoding="utf-8"
        )
        (target_dir / "assets" / "sample.txt").write_text(
            f"Sample asset template for {canonical_skill_name}\n",
            encoding="utf-8"
        )
        (target_dir / "examples" / "example_usage.py").write_text(
            f'''"""
Example usage pattern for {canonical_skill_name}.
"""

# Example: executing {canonical_skill_name}
# Run with: python scripts/{primary_script}.py --help
''',
            encoding="utf-8"
        )

        # 4. Google ADK 2.0 公式 EvalSet 評価データセット（単一真実源: SSOT）の配置
        # 白書 Section 4 (Page 22): 90% 精度保証のため 3つの正例と 3つの負例（境界ケース）の計6件を先行定義
        pos_cases = [
            {
                "eval_id": f"{canonical_dir_name}_001",
                "case_id": f"{canonical_dir_name}_001",
                "expected_skill": canonical_skill_name,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_001",
                        "user_content": {"role": "user", "parts": [{"text": f"Please execute {skill_name_spaced} workflow with --help parameter"}]},
                        "final_response": {"role": "model", "parts": [{"text": "usage_help"}]},
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "run_skill_script",
                                    "args": {
                                        "skill_name": canonical_skill_name,
                                        "file_path": f"scripts/{primary_script}.py",
                                        "args": ["--help"]
                                    }
                                }
                            ]
                        }
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_001_1",
                        "rubric_content": {"text_property": f"correctly invokes run_skill_script with {primary_script}.py"},
                        "type": "TOOL_USE_QUALITY"
                    },
                    {
                        "rubric_id": f"r_{canonical_dir_name}_001_2",
                        "rubric_content": {"text_property": "verifies execution output without cluttering context window"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            },
            {
                "eval_id": f"{canonical_dir_name}_002",
                "case_id": f"{canonical_dir_name}_002",
                "expected_skill": canonical_skill_name,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_002",
                        "user_content": {"role": "user", "parts": [{"text": f"Run {canonical_skill_name} task for target data"}]},
                        "final_response": {"role": "model", "parts": [{"text": "execution_confirmation"}]},
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "run_skill_script",
                                    "args": {
                                        "skill_name": canonical_skill_name,
                                        "file_path": f"scripts/{primary_script}.py",
                                        "args": {"input": "sample_value"}
                                    }
                                }
                            ]
                        }
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_002_1",
                        "rubric_content": {"text_property": f"runs run_skill_script with {primary_script}.py inputs"},
                        "type": "TOOL_USE_QUALITY"
                    },
                    {
                        "rubric_id": f"r_{canonical_dir_name}_002_2",
                        "rubric_content": {"text_property": "preserves data structure"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            },
            {
                "eval_id": f"{canonical_dir_name}_003",
                "case_id": f"{canonical_dir_name}_003",
                "expected_skill": canonical_skill_name,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_003",
                        "user_content": {"role": "user", "parts": [{"text": f"Process batch operations using {canonical_skill_name}"}]},
                        "final_response": {"role": "model", "parts": [{"text": "batch_result"}]},
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "run_skill_script",
                                    "args": {
                                        "skill_name": canonical_skill_name,
                                        "file_path": f"scripts/{primary_script}.py",
                                        "args": {"input": "batch_item_1"}
                                    }
                                }
                            ]
                        }
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_003_1",
                        "rubric_content": {"text_property": f"executes {canonical_skill_name} deterministically"},
                        "type": "TOOL_USE_QUALITY"
                    },
                    {
                        "rubric_id": f"r_{canonical_dir_name}_003_2",
                        "rubric_content": {"text_property": "handles input without hallucinating extra tools"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            }
        ]

        neg_cases = [
            {
                "eval_id": f"{canonical_dir_name}_neg_001",
                "case_id": f"{canonical_dir_name}_neg_001",
                "expected_skill": None,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_neg_001",
                        "user_content": {"role": "user", "parts": [{"text": "What is the capital of France?"}]},
                        "final_response": {"role": "model", "parts": [{"text": "Paris"}]},
                        "intermediate_data": {"tool_uses": []}
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_neg_001_1",
                        "rubric_content": {"text_property": f"does not trigger {canonical_skill_name}"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            },
            {
                "eval_id": f"{canonical_dir_name}_neg_002",
                "case_id": f"{canonical_dir_name}_neg_002",
                "expected_skill": None,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_neg_002",
                        "user_content": {"role": "user", "parts": [{"text": "Summarize the architectural differences between monolithic and microservice systems"}]},
                        "final_response": {"role": "model", "parts": [{"text": "architectural_summary"}]},
                        "intermediate_data": {"tool_uses": []}
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_neg_002_1",
                        "rubric_content": {"text_property": f"does not trigger {canonical_skill_name}"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            },
            {
                "eval_id": f"{canonical_dir_name}_neg_003",
                "case_id": f"{canonical_dir_name}_neg_003",
                "expected_skill": None,
                "conversation": [
                    {
                        "invocation_id": f"inv_{canonical_dir_name}_neg_003",
                        "user_content": {"role": "user", "parts": [{"text": f"Explain the theory behind {skill_name_spaced} without running any tools or scripts"}]},
                        "final_response": {"role": "model", "parts": [{"text": "theoretical_explanation"}]},
                        "intermediate_data": {"tool_uses": []}
                    }
                ],
                "rubrics": [
                    {
                        "rubric_id": f"r_{canonical_dir_name}_neg_003_1",
                        "rubric_content": {"text_property": f"does not invoke run_skill_script for {canonical_skill_name}"},
                        "type": "FINAL_RESPONSE_QUALITY"
                    }
                ]
            }
        ]

        all_cases = pos_cases + neg_cases
        initial_edd_set = {
            "eval_set_id": f"{canonical_skill_name}_edd",
            "name": f"{canonical_skill_name}_edd",
            "description": f"Google ADK 2.0 Native EvalSet for {canonical_skill_name}",
            "skill_name": canonical_skill_name,
            "eval_cases": all_cases
        }
        json_content = json.dumps(initial_edd_set, indent=2, ensure_ascii=False)
        # Google ADK 2.0 公式ディレクトリ自動探索規約 (*.test.json)
        (target_dir / "tests" / f"{canonical_skill_name}.test.json").write_text(
            json_content,
            encoding="utf-8"
        )

        # 5. Google ADK 2.0 公式 EvalConfig 設定ファイル (test_config.json) の配置
        # adk eval CLI および AgentEvaluator が自動探索・ロードする標準評価構成
        test_config = {
            "criteria": {
                "tool_trajectory_avg_score": {
                    "threshold": 1.0,
                    "match_type": "IN_ORDER"
                },
                "rubric_based_final_response_quality_v1": {
                    "threshold": 0.8,
                    "rubrics": [
                        {
                            "rubric_id": "general_quality",
                            "rubric_content": {
                                "text_property": "The final response accurately satisfies the user intent cleanly without conversational filler."
                            }
                        }
                    ],
                    "judge_model_options": {
                        "judge_model": "gemini-2.5-flash",
                        "num_samples": 3
                    }
                }
            }
        }
        (target_dir / "tests" / "test_config.json").write_text(
            json.dumps(test_config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return target_dir


