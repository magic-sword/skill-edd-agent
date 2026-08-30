---
name: case-converter
description: This skill should be used when users need to perform case-converter tasks and workflows.
license: Complete terms in LICENSE.txt
pattern: task_based
---

# Case Converter

## Overview

文字列を大文字(UPPER), 小文字(lower), キャメルケース(camelCase), スネークケース(snake_case)に変換するテキスト変換ユーティリティスキルを作成してください。

## Quick Start

Execute standard operations using the provided modular tools and scripts.

## Available Tasks

### Task 1: Validate Inputs *(Tool: `scripts/case_converter.py`)*

Check required input parameters before execution.

### Task 2: Execute Logic *(Tool: `scripts/case_converter.py`)*

Run scripts/case_converter.py to perform the main operation.

### Task 3: Verify Output

Verify the output format and return the result to the user.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:

- "Please execute case-converter on the input data."
- "Help me run case-converter workflow."

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):

- Simple one-line shell commands that do not need a specialized skill.
- Unrelated domain operations.

## Bundled Resources

### `scripts/` (Executable Tools)
Deterministic execution scripts that run directly in the environment:

- **`scripts/case_converter.py`**: Core execution CLI tool for case-converter

### `references/` (On-Demand Knowledge)
Documentation and schema specifications loaded only when explicitly needed:

- **`references/guide.md`**: Usage guide and reference material for case-converter

## Guidelines & Best Practices

- Ensure all scripts support --help and handle edge cases gracefully.
- Follow Anthropic Markdown-First and Google ADK Progressive Disclosure principles.
