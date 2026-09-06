---
name: skill-reviewer
description: |
  Audits and reviews Agent Skills for architectural soundness, anti-overfitting, and whitepaper quality standards.
  Use when reviewing newly drafted or modified skills, checking for test-case gaming, or auditing SKILL.md before tier promotion.
  Do NOT use for basic deterministic syntax linting (use `edd validate`) or authoring new skills (use `skill-autonomous-builder`).
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: review
---

# Skill Reviewer

## When to use
- Review newly generated or modified Agent Skills before evaluation or tier promotion
- Audit scripts for test-case overfitting, hardcoded input pattern matching, or fragile logic
- Inspect `SKILL.md` for verb-led description, trigger keywords, When NOT to use clauses, and absence of template placeholders
- Generate an objective review report with actionable architectural critique

## When NOT to use
- Deterministic static syntax checking (use `edd validate` instead)
- Writing or scaffolding new skills from scratch (use `skill-autonomous-builder` or `skill-creator`)
- Running production agent applications

## Workflow
1. **Deterministic Gate Check**: Run `edd validate <skill_path>` to ensure the skill passes all static format and structure checks. If invalid, reject immediately.
2. **Audit Scan**: Run the audit helper script to inspect test coverage and scan for multi-line string literal leaks or test-specific variable names:
   ```bash
   python .agents/skills/skill-reviewer/scripts/audit_skill.py --skill-dir src/skills/<skill_name>
   ```
3. **Qualitative Rubric Review**: Review the code against `references/review_rubrics.md`:
   - Verify that `scripts/` implements a general multi-stage pipeline (parse ➔ internal data model ➔ render) rather than pattern-matching test cases.
   - Verify that `SKILL.md` has concrete scenario descriptions with zero placeholder residue (`{task}`, `<TODO>`).
   - Verify that `tests/*.test.json` has at least 3 positive and 3 negative triggers.
4. **Report & Feedback Delivery**: Output the structured Review Report with verdict (`PASS` or `REVISE_REQUIRED`) and actionable rationale for any failed dimensions.

## Examples
- Input: "Review skill markdown-table-formatter" → Output: Complete audit report assessing anti-overfitting, tooling separation, quality bar, and error handling with clear PASS/REVISE verdict.

## Output format
- Return structured Markdown containing Audit Report, Completed Rubric Checklist, Verdict (`PASS` or `REVISE_REQUIRED`), and Actionable Rationale without conversational filler.

## Anti-patterns to avoid
- Do not add negative instructions ("NEVER", "ALWAYS") to prompts when reviewing; provide architectural rationale instead (Whitepaper Page 49).
- Do not approve skills that pass tests by hardcoding test-case inputs or pattern-matching raw input strings.
- Do not duplicate deterministic checks that are already performed by `edd validate`.

## Requirements & Prerequisites
- Python: >= 3.10
- Package: edd-agent-tools

## Bundled Resources
### `scripts/` (Deterministic Audit Tool)
- `scripts/audit_skill.py`: Scans AST for hardcoded test comparisons and compiles test coverage statistics.

### `references/` (Review Standards)
- `references/review_rubrics.md`: 4-dimension evaluation rubrics (Anti-Overfitting, Tooling Separation, Quality Bar, Robustness).
