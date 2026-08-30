#!/usr/bin/env python3
"""
Skill Initializer - Zero-dependency script to create a new skill from template.

Usage:
    init_skill.py <skill-name> --path <path> [--pattern {workflow,task_based,reference,capabilities}]
"""

import sys
import os
import argparse
from pathlib import Path

SKILL_TEMPLATE_WORKFLOW = """---
name: {name}
description: This skill should be used when [TODO: Specific trigger scenarios, file types, or tasks that trigger this workflow].
license: Complete terms in LICENSE.txt
pattern: workflow
---

# {title}

## Overview

[TODO: 1-2 sentences explaining what this skill enables.]

## Workflow Decision Tree

- **If** [Condition A] ➔ **Then** `scripts/{script_name} --action action_a` を実行する
- **If** [Condition B] ➔ **Then** `references/guide.md` を参照する

## Step-by-Step Instructions

### Step 1: 要件の確認と入力検証 *(Target: `scripts/{script_name}`)*

入力パラメータおよび対象ファイルが存在するか検証する。

### Step 2: 処理の実行 *(Target: `scripts/{script_name}`)*

`scripts/{script_name} --help` を確認の上、適切な引数を指定して決定論的に実行する。

## Usage Scenarios & Trigger Examples

- "Example trigger request 1"
- "Example trigger request 2"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/{script_name}`**: 主要処理を実行する CLI / Python API スクリプト

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 処理ルールおよびスキーマ仕様書

## Guidelines & Best Practices

- スクリプトは必ず `--help` でオプションを確認した上で直接コマンドラインから実行すること。
- 未使用の空ディレクトリは削除し、必要なリソースのみを保持すること。
"""

EXAMPLE_SCRIPT = """#!/usr/bin/env python3
\"\"\"
Main execution script for {name}
\"\"\"

import argparse
import sys

def run(input_val: str | None = None) -> str:
    \"\"\"主要タスクを実行します。\"\"\"
    print(f"Executing {name} with input: {{input_val}}")
    return "Success"

def main():
    parser = argparse.ArgumentParser(description="{title} execution script.")
    parser.add_argument("--input", "-i", type=str, help="Input argument or file path")
    args = parser.parse_args()

    run(args.input)
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

EXAMPLE_REFERENCE = """# Reference Guide for {title}

This document contains detailed domain knowledge, API schemas, or guidelines.

## Specifications
- Rule 1: [Specification details]
- Rule 2: [Specification details]
"""


def init_skill(name: str, output_path: str | Path, pattern: str = "workflow") -> Path:
    """新規スキルのディレクトリ構造と初期ファイルを生成します。"""
    base_dir = Path(output_path).resolve()
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    title = name.replace("-", " ").title()
    script_name = f"{name.replace('-', '_')}.py"

    # SKILL.md 生成
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        SKILL_TEMPLATE_WORKFLOW.format(name=name, title=title, script_name=script_name),
        encoding="utf-8"
    )

    # scripts/ 生成
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    script_file = scripts_dir / script_name
    script_file.write_text(EXAMPLE_SCRIPT.format(name=name, title=title), encoding="utf-8")
    script_file.chmod(0o755)

    # references/ 生成
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(exist_ok=True)
    guide_md = refs_dir / "guide.md"
    guide_md.write_text(EXAMPLE_REFERENCE.format(title=title), encoding="utf-8")

    return skill_dir


def main():
    parser = argparse.ArgumentParser(description="Initialize a new skill directory from template.")
    parser.add_argument("name", help="スキル名（lowercase hyphen-case）")
    parser.add_argument("--path", "-p", default="src/skills", help="出力先親ディレクトリ（デフォルト: src/skills）")
    parser.add_argument("--pattern", choices=["workflow", "task_based", "reference", "capabilities"], default="workflow", help="スキルパターン")
    args = parser.parse_args()

    skill_dir = init_skill(args.name, args.path, args.pattern)
    print(f"✅ Successfully initialized skill '{args.name}' at: {skill_dir}")


if __name__ == "__main__":
    main()
