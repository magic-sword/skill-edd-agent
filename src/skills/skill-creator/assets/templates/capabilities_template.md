---
name: {skill_name}
description: |
  Provides multi-capability operations for {skill_description_context}.
  Use when the user asks to execute multi-mode workflows or complex operations with {skill_name}.
  Do NOT use for simple one-off commands or isolated script runs.
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: capabilities
---

# {Skill Title}

## When to use
- Perform {capability_1} using {skill_name}
- Execute {capability_2} on target data

## When NOT to use
- Simple one-off shell operations (use native terminal tools)
- Skill testing, diagnosis, and evolution (use `skill-evolver`)
- New skill creation or packaging (use `skill-creator`)

## Workflow
1. Identify Target Mode: Determine which capability mode (e.g. mode1 or mode2) applies to the user request.
2. Execute Core Script: Run the multi-capability CLI script with appropriate flags:
   ```bash
   python scripts/{primary_script}.py --mode mode1 <arguments>
   ```
3. Inspect and Confirm: Validate that the operation completed successfully without errors.

## Examples
- Input: "Execute mode1 on sample data with {skill_name}" → Output: "Capability mode1 completed successfully"

## Output format
- Return structured status confirmation and output artifacts.

## Anti-patterns to avoid
- Do not run unknown modes without verifying arguments via `--help`.
- Do not mix independent operations into an unverified monolithic execution.

## Requirements & Prerequisites
- Python: >= 3.10

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- `scripts/{primary_script}.py`: Multi-mode execution script.

### `references/` (On-Demand Knowledge)
- `references/guide.md`: Specifications and module documentation.

### `examples/` (Usage Patterns)
- `examples/example_usage.py`: Example configurations and mode invocation patterns.
