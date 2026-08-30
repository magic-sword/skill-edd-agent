---
name: {skill_name}
description: This skill should be used when users need to perform {skill_description_context}.
license: MIT
pattern: workflow
---

# {Skill Title}

## Overview

{Brief overview of the workflow and domain context.}

## Workflow Decision Tree

To determine the appropriate procedure, follow this decision logic:

- **If** {Condition A} ➔ **Then** {Action A / scripts/step_a.py}
- **If** {Condition B} ➔ **Then** {Action B / references/guide.md}

## Step-by-Step Instructions

### Step 1: Input Validation and Setup *(Tool: `scripts/{primary_script}.py`)*

To validate prerequisites and parse arguments:
```bash
python scripts/{primary_script}.py --check
```

### Step 2: Core Execution *(Tool: `scripts/{primary_script}.py`)*

To execute the workflow:
```bash
python scripts/{primary_script}.py <arguments>
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
