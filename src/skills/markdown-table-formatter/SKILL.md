---
name: markdown-table-formatter
description: |
  Format, align, and clean up markdown tables in text strings or files with deterministic column padding and alignment markers.
  Use when the user asks to format a markdown table, align table columns, or clean up unaligned markdown files.
  Do NOT use for CSV/Excel manipulation, non-table document formatting, or system administration tasks.
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: workflow
---

# Markdown Table Formatter

## When to use
- Format unaligned markdown tables in markdown files or text snippets
- Align table columns with left (`:---`), center (`:---:`), or right (`---:`) markers
- Ensure uniform column widths and consistent cell padding across all table rows

## When NOT to use
- Formatting non-table markdown elements like headings, lists, or blockquotes
- Spreadsheet, CSV, or database data conversions
- Skill testing, diagnosis, and evolution (use `skill-evolver`)
- New skill scaffolding or packaging (use `skill-creator`)

## Workflow
1. Reconnaissance and Input Inspection: Inspect target markdown content or file path to ensure it contains table data.
2. Core Execution: Execute the deterministic formatting script:
   ```bash
   python scripts/markdown_table_formatter.py "| Name | Age |\n|---|---|\n| Alice | 30 |"
   # Or for a file:
   python scripts/markdown_table_formatter.py docs/reference.md
   ```
3. Result Verification: Verify formatted table columns are cleanly aligned and return the result.

## Examples
- Input:
  ```markdown
  | Item | Qty |
  |---|---|
  | Widget | 10 |
  ```
  Output:
  ```markdown
  | Item   | Qty |
  |--------|-----|
  | Widget | 10  |
  ```

## Output format
- Return the cleanly aligned markdown table directly, maintaining delimiters and alignment specifiers without conversational filler.

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
