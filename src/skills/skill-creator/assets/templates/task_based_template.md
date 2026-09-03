---
name: {skill_name}
description: |
  Provides specialized utilities and operations for {skill_title}.
  Use when the user asks to perform operations on {skill_name}, execute conversion or processing tasks.
  Do NOT use for one-line shell commands or global environment configuration.
license: MIT
pattern: task_based
---

# {skill_title}

## When to use
- Perform {task} operations on input text or files
- Convert, format, or process data using {skill_name} utilities

## When NOT to use
- Trivial operations solvable with single-line shell commands
- Global system administration or environment setup
- Skill testing, diagnosis, and evolution (use `skill-evolver`)
- New skill creation or packaging (use `skill-creator`)

## Workflow
1. Identify Input and Options: Determine target input text or files, options, and output destination.
2. Execute Utility Script: Run the deterministic CLI script:
   ```bash
   python scripts/{primary_script}.py --input "data"
   ```
3. Verify Result: Check the output format and return the result.

## Examples
- Input: "Process 'sample_input' with {skill_name}" → Output: "Processed output"

## Output format
- Return direct operational output or processed file path.

## Anti-patterns to avoid
- Do not read script source code into context; check CLI options with `--help`.
- Do not make breaking edits to unrelated files.

## Requirements & Prerequisites
- Python: >= 3.10

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- `scripts/{primary_script}.py`: Deterministic utility tool.

### `references/` (On-Demand Knowledge)
- `references/guide.md`: Detailed tool guidelines and options.

### `examples/` (Usage Patterns)
- `examples/example_usage.py`: Example commands and recipes.
