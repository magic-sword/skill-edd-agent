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
description: This skill should be used when users need to perform {skill_name_spaced} tasks.
license: MIT
pattern: {pattern}
---

# {skill_title}

## Overview

Enables specialized execution of {skill_name_spaced} workflows.

## Step-by-Step Instructions

### Step 1: Initialize and Validate Inputs *(Tool: `scripts/{primary_script}.py`)*
To verify input parameters, inspect incoming arguments before execution.

### Step 2: Execute Core Logic *(Tool: `scripts/{primary_script}.py`)*
To execute the task, run `scripts/{primary_script}.py` with the appropriate parameters.

## Usage Scenarios & Trigger Examples

- "Please help me execute {skill_name} on target data."

## When NOT to Use This Skill

- Simple one-off commands that do not require specialized workflow execution.

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/{primary_script}.py`**: Core CLI tool for {skill_title}.

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Detailed reference documentation.

## Guidelines & Best Practices

- Always verify arguments before execution.
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
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill_name):
            raise ValueError(f"Skill name '{skill_name}' must be lowercase hyphen-case (e.g. pdf-tools)")

        target_dir = Path(output_base_dir).resolve() / skill_name
        if target_dir.exists():
            raise FileExistsError(f"Target skill directory already exists: {target_dir}")

        target_dir.mkdir(parents=True, exist_ok=False)
        (target_dir / "scripts").mkdir(exist_ok=True)
        (target_dir / "references").mkdir(exist_ok=True)
        (target_dir / "assets").mkdir(exist_ok=True)
        (target_dir / "tests").mkdir(exist_ok=True)
        (target_dir / "tests" / "results").mkdir(exist_ok=True)

        skill_title = skill_name.replace("-", " ").title()
        skill_name_spaced = skill_name.replace("-", " ")
        primary_script = skill_name.replace("-", "_")

        # 1. テンプレートの探索と読み込み（SSOT: パッケージ組み込み templates/ または明示指定）
        template_content = None
        cand_dirs = []
        if templates_dir:
            cand_dirs.append(Path(templates_dir).resolve())
        # パッケージ同梱の標準テンプレートディレクトリ
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
        rendered_md = template_content.replace("{skill_name}", skill_name)
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
    print(f"Executing {skill_name} with input: {{input_val}}")
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

        # 3. リファレンス・アセットの配置
        (target_dir / "references" / "guide.md").write_text(
            f"# Reference Guide for {skill_title}\n\nDetailed specifications and reference material for {skill_name}.\n",
            encoding="utf-8"
        )
        (target_dir / "assets" / "sample.txt").write_text(
            f"Sample asset template for {skill_name}\n",
            encoding="utf-8"
        )

        # 4. 初期テストおよび評価セット（Stage 3 契約・トリガーハーネス）の配置
        contract_test_code = f'''"""
Contract test for {skill_name} CLI and tools.
"""

import sys
import subprocess
from pathlib import Path


def test_cli_help():
    script_path = Path(__file__).parent.parent / "scripts" / "{primary_script}.py"
    assert script_path.exists(), f"Script {{script_path}} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "{skill_title}" in res.stdout or "usage" in res.stdout.lower()
'''
        (target_dir / "tests" / f"test_{primary_script}_contract.py").write_text(contract_test_code, encoding="utf-8")


        initial_evalset = {
            "eval_set_id": f"{skill_name}_contract",
            "skill_name": skill_name,
            "eval_cases": [
                {
                    "eval_case_id": f"{skill_name}_cli_help",
                    "function_name": "CLI",
                    "script_name": f"{primary_script}.py",
                    "cli_args": ["--help"],
                    "expected_exit_code": 0,
                    "expected": "usage"
                }
            ]
        }
        (target_dir / "tests" / f"{skill_name}_contract.evalset.json").write_text(
            json.dumps(initial_evalset, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        initial_trigger_set = {
            "eval_set_id": f"{skill_name}_trigger",
            "skill_name": skill_name,
            "cases": [
                {
                    "eval_case_id": f"{skill_name}_trigger_positive",
                    "user_input": f"Please help me perform {skill_name_spaced} workflow on my data.",
                    "should_trigger": True
                },
                {
                    "eval_case_id": f"{skill_name}_trigger_negative",
                    "user_input": "What is the capital of France?",
                    "should_trigger": False
                }
            ]
        }
        (target_dir / "tests" / f"{skill_name}_trigger.evalset.json").write_text(
            json.dumps(initial_trigger_set, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return target_dir

