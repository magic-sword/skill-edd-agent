---
name: {skill_name}
description: This skill should be used when users need to perform {skill_description_context}.
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

### Step 1: Input Validation and Setup *(Tool: `scripts/{primary_script}.py`)*

To validate prerequisites and parse arguments:
```bash
python scripts/{primary_script}.py --input "data"
```

### Step 2: Core Execution *(Tool: `scripts/{primary_script}.py`)*

To execute the workflow:
```bash
python scripts/{primary_script}.py --input "data"
```

### Step 3: Result Verification and Output

To verify the generated output and present the final response to the user.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:
- "Please execute {task} on the target files."
- "Run the {skill_name} workflow."

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios:
- **Simple one-liner operations**: Use native shell commands directly.
- **Out of scope tasks**: Use specialized skills instead.

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/{primary_script}.py`**: Deterministic CLI tool for the workflow.

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Specifications and domain guidelines.

## Guidelines & Best Practices
- Verify inputs before executing operations.
- Ensure all scripts support `--help` and use Python standard libraries.
