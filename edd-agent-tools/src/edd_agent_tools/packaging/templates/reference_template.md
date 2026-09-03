---
name: {skill_name}
description: |
  Provides architectural references and domain guidelines for {skill_title}.
  Use when the user asks for specifications, design rules, or best practices for {skill_name}.
  Do NOT use for automated code execution or active script modification.
license: MIT
allowed-tools: load_skill_resource
pattern: reference
---

# {skill_title}

## When to use
- What are the design guidelines for {skill_name}?
- Review this specification against our {skill_name} standard

## When NOT to use
- Automated code execution or active script modification (use workflow skills)
- Skill testing, diagnosis, and evolution (use `skill-evolver`)
- New skill creation or packaging (use `skill-creator`)

## Workflow
1. Identify Relevant Topic: Clarify the domain area, specification, or question being asked.
2. Consult Reference Knowledge: Read relevant sections in `references/guide.md` or `examples/`.
3. Provide Grounded Guidance: Deliver recommendations strictly grounded in the reference materials.

## Examples
- Input: "What is the recommended architecture for {skill_name}?" → Output: "Architecture guidance referencing guide.md"

## Output format
- Provide clear, structured documentation with citations to reference files.

## Anti-patterns to avoid
- Do not fabricate rules or schemas not documented in `references/`.
- Do not dump thousands of lines into the context without verifying relevance.

## Requirements & Prerequisites
- Python: >= 3.10

## Bundled Resources
### `references/` (On-Demand Knowledge)
- `references/guide.md`: Specifications and domain guidelines.

### `examples/` (Reference Patterns)
- `examples/example_usage.md`: Architectural patterns and reference implementations.
