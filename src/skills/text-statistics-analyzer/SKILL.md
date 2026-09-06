---
name: text-statistics-analyzer
description: |
  Analyzes and computes text statistics, including character counts, word counts, sentence counts, and estimated reading time for strings and document files.
  Use when the user asks to measure text length, count characters or words, calculate reading time, or extract basic textual frequency metrics.
  Do NOT use for summarizing text content, translating languages, proofreading grammar, or performing sentiment analysis.
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: task_based
  tier: 1
---

# Text Statistics Analyzer

## When to use
- Calculate precise character counts (with/without whitespace), word counts, sentence counts, and paragraph counts for raw text or files
- Estimate reading time based on standard CJK (500 CPM) or Latin (200 WPM) reading speed benchmarks
- Extract high-frequency terms from input text without conversational padding
- Format textual metrics as a Markdown table or machine-readable JSON

## When NOT to use
- Summarizing or condensing articles (perform standard response or invoke a summarization workflow)
- Translating text across languages (perform translation directly)
- Grammatical linting or code style formatting (use appropriate code linters or formatter skills)
- Simple single-line echo/print operations

## Workflow
1. **Input Identification**:
   Determine whether the input is provided as raw text or a file path. Identify requested output format (`markdown` or `json`).
2. **Deterministic Computation**:
   Execute the bundled Python script with `run_skill_script`. Let the deterministic code perform counting and reading time calculations to eliminate LLM arithmetic hallucinations:
   ```bash
   python scripts/text_statistics_analyzer.py --input "<text_or_path>" --format markdown
   ```
3. **Structured Rendering**:
   Output the resulting table or JSON cleanly without conversational filler or redundant preamble.

## Examples
- **Input**: "Analyze text statistics for 'Hello world! This is a simple test text.'"
  **Output**:
  | Metric | Value |
  |---|---|
  | Characters (total) | 40 |
  | Characters (no spaces) | 33 |
  | Words | 8 |
  | Sentences | 2 |
  | Paragraphs | 1 |
  | Estimated Reading Time | < 1 min |

- **Input**: "日本語テキストの統計情報を計算して: '吾輩は猫である。名前はまだ無い。'"
  **Output**:
  | 指標 | 値 |
  |---|---|
  | 文字数（全体） | 18 |
  | 文字数（空白除く） | 18 |
  | 単語数（相当） | 16 |
  | 文数 | 2 |
  | 段落数 | 1 |
  | 推定読了時間 | < 1分 |

## Output format
- For general requests, present a structured GitHub-Flavored Markdown table displaying calculated metrics.
- When `--format json` is requested, return valid JSON containing integer counts and estimated reading duration.
- Exclude conversational filler such as "Here is the result you requested".

## Anti-patterns to avoid
- Relying on LLM internal token counting or mental arithmetic: Token counts do not correspond 1:1 to characters or words. Always invoke `scripts/text_statistics_analyzer.py` for deterministic precision.
- Cluttering the context window with the Python script source code: The script is designed as a black box tool invoked via `run_skill_script`.
- Triggering this skill for semantic summarization or language translation tasks: Check `## When NOT to use` to prevent over-triggering.

## Requirements & Prerequisites
- Python: >= 3.10
- Dependencies: Standard library only (`re`, `argparse`, `json`, `math`, `collections`, `pathlib`)

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- `scripts/text_statistics_analyzer.py`: Deterministic text statistics engine. Supports CLI arguments `--input`, `--format`, `--wpm`, `--cpm`.

### `references/` (On-Demand Knowledge)
- `references/metrics_guide.md`: Reading speed benchmarks (WPM/CPM) and CJK character ratio classification rules.
