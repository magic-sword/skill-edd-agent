#!/usr/bin/env python3
"""
Skill Initializer CLI - Zero-dependency Skill Directory Scaffold Generator
Anthropic / Google ADK 2.0 準拠のスキル雛形を Python 標準ライブラリのみで高速生成します。
`assets/templates/*.md` の Markdown テンプレートを真実源（SSOT）として読み込んで展開します。

Usage:
    init_skill.py <skill-name> --path <path> [--pattern {workflow,task_based,reference,capabilities}]
"""

import sys
import os
import re
import argparse
from pathlib import Path

SKILL_PATTERNS = ["workflow", "task_based", "reference", "capabilities"]

# フォールバック用最小限テンプレート
DEFAULT_FALLBACK_TEMPLATE = """---
name: {skill_name}
description: This skill should be used when users need to perform {skill_description_context}.
license: MIT
pattern: {pattern}
---

# {skill_title}

## Overview

{skill_title} を実行するための専門ワークフロー。

## Step-by-Step Instructions

### Step 1: 入力パラメータの検証 *(Tool: `scripts/{primary_script}.py`)*
To verify inputs and check prerequisites, inspect user parameters before execution.

### Step 2: コアロジックの実行 *(Tool: `scripts/{primary_script}.py`)*
To execute the main task, run `scripts/{primary_script}.py` with the required arguments.

### Step 3: 結果の確認と出力
To finalize the workflow, format and present the output to the user.

## Usage Scenarios & Trigger Examples

- "Please help me execute {skill_name} on the target data."

## When NOT to Use This Skill

- **単純なワンライナーのシェルコマンドで完了する操作**: スキルをロードせず直接実行する。

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/{primary_script}.py`**: {skill_title} のコア実行スクリプト（CLI対応）

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 詳細な仕様書およびリファレンスドキュメント

## Guidelines & Best Practices

- 実行前に必ずパラメータの妥当性を確認すること。
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


def load_template_for_pattern(pattern: str) -> str:
    """`assets/templates/{pattern}_template.md` を探索・ロードします。"""
    script_dir = Path(__file__).parent
    skill_root = script_dir.parent
    template_path = skill_root / "assets" / "templates" / f"{pattern}_template.md"

    if template_path.exists():
        try:
            return template_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # グローバルな探索パス
    alt_paths = [
        Path("src/skills/skill-creator/assets/templates") / f"{pattern}_template.md",
        Path("skills/skill-creator/assets/templates") / f"{pattern}_template.md",
    ]
    for p in alt_paths:
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                pass

    return DEFAULT_FALLBACK_TEMPLATE


def safe_format_template(template_str: str, context: dict) -> str:
    """未定義プレースホルダがあっても安全に置換するフォーマッタ"""
    def _replace(match):
        key = match.group(1).strip()
        return str(context.get(key, f"{{{key}}}"))

    return re.sub(r"\{([a-zA-Z0-9_ ]+)\}", _replace, template_str)


def init_skill(skill_name: str, path: str = "src/skills", pattern: str = "workflow") -> Path | None:
    """Zero-dependency で新しいスキルディレクトリを初期化します。"""
    if pattern not in SKILL_PATTERNS:
        print(f"❌ Error: Invalid pattern '{pattern}'. Choices: {SKILL_PATTERNS}", file=sys.stderr)
        return None

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill_name):
        print(f"❌ Error: Skill name '{skill_name}' must be lowercase hyphen-case (e.g. pdf-tools)", file=sys.stderr)
        return None

    target_dir = Path(path).resolve() / skill_name
    if target_dir.exists():
        print(f"❌ Error: Target skill directory already exists: {target_dir}", file=sys.stderr)
        return None

    target_dir.mkdir(parents=True, exist_ok=False)
    skill_title = skill_name.replace("-", " ").title()
    primary_script = skill_name.replace("-", "_")

    # 1. SKILL.md の書き出し（テンプレートから置換）
    raw_template = load_template_for_pattern(pattern)
    template_ctx = {
        "skill_name": skill_name,
        "skill_title": skill_title,
        "Skill Title": skill_title,
        "skill_description_context": f"{skill_title} workflows and operations",
        "pattern": pattern,
        "primary_script": primary_script,
        "task": f"{skill_title} processing",
        "task_name": "sample-task",
        "target": "data",
        "input": "input data",
        "capability_1": "Capability One",
        "capability_2": "Capability Two"
    }
    skill_md = safe_format_template(raw_template, template_ctx)
    (target_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 2. scripts/
    scripts_dir = target_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    sample_script = scripts_dir / f"{primary_script}.py"
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
