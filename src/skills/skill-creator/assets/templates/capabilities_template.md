---
name: {skill_name}
description: This skill should be used when users need multiple integrated capabilities and operations for {skill_description_context}.
license: MIT
pattern: capabilities
---

# {Skill Title}

## Overview

{Brief overview of the integrated capabilities and operational domain.}

## Core Capabilities

### 1. Capability One *(Module: `scripts/{primary_script}.py`)*

To execute the first capability:
```bash
python scripts/{primary_script}.py --mode mode1 <arguments>
```

### 2. Capability Two *(Module: `scripts/{primary_script}.py`)*

To execute the second capability:
```bash
python scripts/{primary_script}.py --mode mode2 <arguments>
```

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:
- "Perform {capability_1} using {skill_name}."
- "Execute {capability_2} on target data."

## When NOT to Use This Skill
- **Simple one-off shell operations**: Use native commands directly.

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/{primary_script}.py`**: Multi-mode execution script.

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Specifications and module documentation.

### `examples/` (Usage Patterns)
- **`examples/example_usage.py`**: Example configurations and mode invocation patterns.

## Guidelines & Best Practices
- **Black-box Execution**: Always inspect options with `python scripts/{primary_script}.py --help` first.
- **Reconnaissance First**: Inspect arguments and operational context before triggering changes.
- Select the appropriate mode/module based on task requirements.
