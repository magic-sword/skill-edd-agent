---
name: {skill_name}
description: |
  Provides architectural references and guidelines for {skill_title}.
  Use when the user asks for domain specifications, design rules, or best practices for {skill_name}.
  Do NOT use for active automated code generation or script execution.
license: MIT
pattern: reference
---

# {skill_title}

## Overview

{skill_title} に関するドメインリファレンスおよび設計ガイドライン。

## Core Principles & Guidelines

### Principle 1: Base Design Rule
Standard architectural constraints and guidelines for {skill_title}.

### Principle 2: Resource Isolation
Keep domain references isolated within `references/`.

## Available Specifications & References

- **`references/guide.md`**: In-depth technical specifications and API definitions.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:
- "What are the design guidelines for {skill_name}?"
- "Review this architecture against our {skill_name} standard."

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios:
- **Active automated code generation or script execution**: Use task-based or workflow skills.

## Bundled Resources

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: Specifications and domain guidelines.

### `examples/` (Reference Patterns)
- **`examples/example_usage.md`**: Example reference structures and architectural patterns.

## Guidelines & Best Practices
- Keep reference documents organized in `references/` and `examples/` for on-demand loading.
