"""
Unit tests for template residue detection in SkillValidator
"""

import pytest
from edd_agent_tools.validation.validator import SkillValidator


def test_validator_detects_task_placeholder():
    content = """---
name: sample-skill
description: |
  Sample skill description for testing purposes.
  Use when testing validation behavior.
  Do NOT use for production.
license: MIT
---
# Sample Skill
## When to use
- Execute {task} on sample files
## When NOT to use
- Production tasks
## Workflow
1. Step 1
## Examples
- Input: test -> Output: test
## Output format
- Pure text
## Anti-patterns to avoid
- Do not run randomly
"""
    res = SkillValidator.validate_content(content)
    assert not res.is_valid
    assert any("Template placeholder residue detected: '{task}'" in err for err in res.errors)


def test_validator_detects_todo_placeholder():
    content = """---
name: sample-skill
description: |
  Sample skill description for testing purposes.
  Use when testing validation behavior.
  Do NOT use for production.
license: MIT
---
# Sample Skill
## When to use
- Valid scenario
## When NOT to use
- Production tasks
## Workflow
1. <TODO> implement this workflow
## Examples
- Input: test -> Output: test
## Output format
- Pure text
## Anti-patterns to avoid
- Do not run randomly
"""
    res = SkillValidator.validate_content(content)
    assert not res.is_valid
    assert any("Template placeholder residue detected: '<TODO>'" in err for err in res.errors)


def test_validator_passes_when_clean():
    content = """---
name: sample-skill
description: |
  Format markdown tables cleanly with proper spacing.
  Use when formatting table text or files.
  Do NOT use for CSV files.
license: MIT
---
# Sample Skill
## When to use
- Format tables in markdown documents
## When NOT to use
- Editing non-table text
## Workflow
1. Run formatting script
## Examples
- Input: test -> Output: test
## Output format
- Pure text
## Anti-patterns to avoid
- Do not overwrite without backup
"""
    res = SkillValidator.validate_content(content)
    assert res.is_valid
    assert len(res.errors) == 0
