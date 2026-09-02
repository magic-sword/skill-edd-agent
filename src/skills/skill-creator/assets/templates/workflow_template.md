---
name: {skill_name}
description: |
  Performs {skill_title} workflows with deterministic execution.
  Use when the user asks to execute {skill_name}, process relevant inputs, or orchestrate this domain task.
  Do NOT use for simple one-off commands or unrelated administrative tasks.
license: MIT
pattern: workflow
---

# {skill_title}

## Overview

{skill_title} を実行するための専門ワークフロー。

## Workflow Decision Tree

To determine the appropriate procedure, follow this decision logic:

- **If** 標準的なリクエストの場合 ➔ **Then** `scripts/{primary_script}.py` を実行して処理を行う
- **If** 特別な設定やスキーマ確認が必要な場合 ➔ **Then** `references/guide.md` を参照する

## Step-by-Step Instructions

### Step 1: Reconnaissance and Input Inspection
To inspect target data, schema, or files before modification, sample the incoming inputs and verify specifications (consult `references/guide.md` or `examples/` if needed).

### Step 2: Core Execution *(Tool: `scripts/{primary_script}.py`)*
To execute the workflow deterministically:
```bash
python scripts/{primary_script}.py --input "data"
```

### Step 3: Result Verification and Output
To verify the generated output matches requirements and return the final response.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:
- "Please execute {task} on the target files."
- "Run the {skill_name} workflow."

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios:
- **粒度境界 (Granularity)**: Simple one-liner operations that do not require structured workflows.
- **技術的限界 (Out-of-Scope)**: Tasks outside the defined domain boundaries.
- **ライフサイクル分離 (Lifecycle)**: Skill testing, diagnosis, and evolution (use `skill-evolver`).
- **インベントリ照合 (Inventory)**: Existing skills in inventory already covering the request.

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/{primary_script}.py`**: Deterministic CLI tool for the workflow.

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Specifications and domain guidelines.

### `examples/` (Usage Patterns)
- **`examples/example_usage.py`**: Example execution patterns and typical configurations.

## Guidelines & Best Practices
- **Black-box Execution**: Always run `python scripts/{primary_script}.py --help` first to inspect arguments without cluttering context window.
- **Reconnaissance First**: Inspect data structure and verify edge cases before applying modifications.
- **Minimal Edits**: Apply targeted modifications without overwriting unrelated structures or metadata.
- Ensure all scripts support `--help` and use Python standard libraries.
