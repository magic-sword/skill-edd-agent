#!/usr/bin/env python3
"""
Skill Initializer CLI - Zero-dependency Skill Directory Scaffold Generator
Anthropic / Google ADK 2.0 準拠のスキル雛形を Python 標準ライブラリのみで高速生成します。

Usage:
    init_skill.py <skill-name> --path <path> [--pattern {workflow,task_based,reference,capabilities}]
"""

import sys
import os
import re
import argparse
from pathlib import Path

SKILL_PATTERNS = ["workflow", "task_based", "reference", "capabilities"]

WORKFLOW_TEMPLATE = """---
name: {skill_name}
description: This skill should be used when users want to perform {skill_title} workflows. It provides step-by-step guidance and deterministic tools.
license: Complete terms in LICENSE.txt
pattern: {pattern}
---

# {skill_title}

## Overview

{skill_title} を実行するための専門ワークフロー。

## Workflow Decision Tree

- **If** 標準的なリクエストの場合 ➔ **Then** `scripts/{script_name}` を実行して処理を行う
- **If** 特別な設定やスキーマ確認が必要な場合 ➔ **Then** `references/guide.md` を参照する

## Step-by-Step Instructions

### Step 1: 入力パラメータの検証 *(Tool: `scripts/{script_name}`)*

To verify inputs and check prerequisites, inspect user parameters before execution.

### Step 2: コアロジックの実行 *(Tool: `scripts/{script_name}`)*

To execute the main task, run `scripts/{script_name}` with the required arguments.

### Step 3: 結果の確認と出力

To finalize the workflow, format and present the output to the user.

## Usage Scenarios & Trigger Examples

- "Please help me execute {skill_name} on the target data."
- "{skill_title} を実行して結果を出力してください。"

## When NOT to Use This Skill

- **単純なワンライナーのシェルコマンドで完了する操作**: スキルをロードせず直接実行する。
- **対象ドメイン外のタスク**: 専用の別スキルを利用する。

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/{script_name}`**: {skill_title} のコア実行スクリプト（CLI対応）

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 詳細な仕様書およびリファレンスドキュメント

### `assets/` (Output Templates & Boilerplates)
- **`assets/sample.txt`**: 出力用テンプレート素材

## Guidelines & Best Practices

- 実行前に必ずパラメータの妥当性を確認すること。
- 不明なエラーが発生した場合は `references/guide.md` を参照すること。
"""

TASK_BASED_TEMPLATE = """---
name: {skill_name}
description: This skill should be used when users require specialized utility tasks for {skill_title}.
license: Complete terms in LICENSE.txt
pattern: {pattern}
---

# {skill_title}

## Overview

{skill_title} に関するユーティリティタスク群を提供します。

## Quick Start

Execute standard operations using the provided modular tools and scripts.

## Available Tasks

### Task 1: 解析と準備
To prepare for execution, inspect inputs and configuration.

### Task 2: ツール実行 *(Tool: `scripts/{script_name}`)*
To perform the operation, execute `scripts/{script_name}`.

### Task 3: 結果出力
To present the results, format the output clearly.

## Usage Scenarios & Trigger Examples

- "Execute {skill_name} task on input data."

## When NOT to Use This Skill

- **極めて単純な操作**: ネイティブコマンドを直接使用する。

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/{script_name}`**: ユーティリティスクリプト

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: タスクガイド

## Guidelines & Best Practices

- タスクの目的に応じて最適なツールを選択すること。
"""

SAMPLE_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
\"\"\"
Core execution script for {skill_name}
\"\"\"

import argparse
import sys

def run(input_val: str | None = None) -> str:
    \"\"\"主要タスクを実行します。\"\"\"
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
"""

def init_skill(skill_name: str, path: str = "src/skills", pattern: str = "workflow") -> Path | None:
    """Zero-dependency で新しいスキルディレクトリを初期化します。"""
    if pattern not in SKILL_PATTERNS:
        print(f"❌ Error: Invalid pattern '{pattern}'. Choices: {SKILL_PATTERNS}")
        return None

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill_name):
        print(f"❌ Error: Skill name '{skill_name}' must be lowercase hyphen-case (e.g. pdf-tools)")
        return None

    target_dir = Path(path).resolve() / skill_name
    if target_dir.exists():
        print(f"❌ Error: Target skill directory already exists: {target_dir}")
        return None

    target_dir.mkdir(parents=True, exist_ok=False)
    skill_title = skill_name.replace("-", " ").title()
    script_name = f"{skill_name.replace('-', '_')}.py"

    # 1. SKILL.md の書き出し
    template = WORKFLOW_TEMPLATE if pattern == "workflow" else TASK_BASED_TEMPLATE
    skill_md = template.format(
        skill_name=skill_name,
        skill_title=skill_title,
        pattern=pattern,
        script_name=script_name
    )
    (target_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 2. scripts/
    scripts_dir = target_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    sample_script = scripts_dir / script_name
    script_code = SAMPLE_SCRIPT_TEMPLATE.format(
        skill_name=skill_name,
        skill_title=skill_title
    )
    sample_script.write_text(script_code, encoding="utf-8")
    try:
        sample_script.chmod(0o755)
    except Exception:
        pass

    # 3. references/
    references_dir = target_dir / "references"
    references_dir.mkdir(exist_ok=True)
    (references_dir / "guide.md").write_text(
        f"# Reference Guide for {skill_title}\n\nDetailed specifications and reference documentation for {skill_name}.\n",
        encoding="utf-8"
    )

    # 4. assets/
    assets_dir = target_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "sample.txt").write_text(f"Sample asset for {skill_name}\n", encoding="utf-8")

    # 5. tests/
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "results").mkdir(exist_ok=True)

    print(f"✅ Successfully initialized skill '{skill_name}' at: {target_dir}")
    return target_dir


def main():
    parser = argparse.ArgumentParser(description="Zero-dependency Skill Initializer CLI")
    parser.add_argument("name", help="Skill name (lowercase hyphen-case, e.g. pdf-tools)")
    parser.add_argument("--path", "-p", default="src/skills", help="Parent directory (default: src/skills)")
    parser.add_argument("--pattern", choices=SKILL_PATTERNS, default="workflow", help="Skill pattern")
    args = parser.parse_args()

    skill_dir = init_skill(args.name, path=args.path, pattern=args.pattern)
    if skill_dir:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
