---
name: markdown-table-formatter
description: |
  Performs Markdown Table Formatter workflows with deterministic execution.
  Use when the user asks to execute markdown-table-formatter, process relevant inputs, or orchestrate this domain task.
  Do NOT use for simple one-off commands or unrelated administrative tasks.
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: workflow
---

# Markdown Table Formatter

## When to use
- Execute {task} on the target files
- Run the markdown-table-formatter workflow

## When NOT to use
- Simple one-liner operations that do not require structured workflows
- Tasks outside the defined domain boundaries
- Skill testing, diagnosis, and evolution (use `skill-evolver`)
- New skill scaffolding or packaging (use `skill-creator`)

## Workflow
1. Reconnaissance and Input Inspection: To inspect target data, schema, or files before modification, sample incoming inputs and verify specifications (consult `references/guide.md` if needed).
2. Core Execution: To execute the workflow deterministically:
   ```bash
   python scripts/markdown_table_formatter.py --input "data"
   ```
3. Result Verification: To verify the generated output matches requirements and return the response.

## Examples
- Input: "Run markdown-table-formatter on sample data" → Output: "Successfully processed sample data"

## Output format
- Return direct operational summary and structured result files.

## Anti-patterns to avoid
- Do not read large scripts into LLM context window without running `--help`.
- Do not blindly overwrite user files without sampling and inspecting input data first.

## Requirements & Prerequisites
- Python: >= 3.10

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- `scripts/markdown_table_formatter.py`: Deterministic CLI tool for the workflow.

### `references/` (On-Demand Knowledge)
- `references/guide.md`: Specifications and domain guidelines.
