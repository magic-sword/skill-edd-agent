---
name: {skill_name}
description: This skill should be used when users need utility tasks for {skill_description_context}.
license: MIT
pattern: task_based
---

# {skill_title}

## Overview

{skill_title} に関するユーティリティタスク群を提供します。

## Quick Start

To execute standard operations using the provided CLI tool:
```bash
python scripts/{primary_script}.py --input "data"
```

## Available Tasks

### Task 1: Inspection & Preparation
To inspect inputs and determine conversion or operation parameters.

### Task 2: Operation Execution *(Tool: `scripts/{primary_script}.py`)*
To perform the required operation:
```bash
python scripts/{primary_script}.py --input "data"
```

### Task 3: Output Verification
To verify the results and return formatted output to the user.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:
- "Please convert/process {input}."
- "Run task {task_name} on {target}."

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios:
- **Trivial operations**: Simple one-word string conversions or native commands.
- **Complex end-to-end workflows**: Use specialized workflow skills instead.

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/{primary_script}.py`**: Deterministic CLI tool for tasks.

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Detailed options and schemas.

### `examples/` (Usage Patterns)
- **`examples/example_usage.py`**: Example command invocations and argument patterns.

## Guidelines & Best Practices
- **Black-box Execution**: Always execute `python scripts/{primary_script}.py --help` first to inspect parameters rather than reading script code into context.
- **Reconnaissance First**: Validate input data formats and edge cases before running operations.
- Ensure script flags and help messages (`--help`) are clear.
