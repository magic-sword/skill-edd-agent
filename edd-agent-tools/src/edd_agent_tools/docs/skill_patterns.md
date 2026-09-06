# Skill Patterns & Architecture Types

All skills are categorized into one of four standard architectural patterns, declared under `metadata.pattern` in the YAML Frontmatter (Google ADK 2.0 compliant). Each pattern follows the Whitepaper Appendix A minimal `SKILL.md` 6 mandatory sections (`## When to use`, `## When NOT to use`, `## Workflow`, `## Examples`, `## Output format`, `## Anti-patterns to avoid`), adapting the content of `## Workflow` and bundled resources to its domain.

---

## 1. Workflow-Based (`workflow`)
- **Best for**: Sequential multi-step processes with conditional branching or phased pipelines.
- **Frontmatter Declaration**:
  ```yaml
  metadata:
    pattern: workflow
  ```
- **Workflow Section Focus**: Phased procedures (e.g. 1. Reconnaissance ➔ 2. Execution ➔ 3. Verification) directing deterministic scripts.
- **Bundled Resources**: Primary CLI scripts in `scripts/`, schema/specs in `references/`.
- **Examples**: `code-refactorer`, `pr-review-pipeline`, `skill-creator`, `skill-evolver`.

---

## 2. Task-Based (`task_based`)
- **Best for**: Collections of standalone utility operations or direct format transformations.
- **Frontmatter Declaration**:
  ```yaml
  metadata:
    pattern: task_based
  ```
- **Workflow Section Focus**: Task selection and deterministic CLI execution with distinct argument flags.
- **Bundled Resources**: Compact standalone CLI scripts in `scripts/` (e.g., zero-dependency utilities).
- **Examples**: `case-converter`, `secret-sanitizer`, `image-converter`.

---

## 3. Reference/Guidelines (`reference`)
- **Best for**: Domain knowledge, coding standards, brand guidelines, or policies without heavy script execution.
- **Frontmatter Declaration**:
  ```yaml
  metadata:
    pattern: reference
  ```
- **Workflow Section Focus**: Topic clarification, reference lookup in `references/`, and grounded guidance generation.
- **Bundled Resources**: In-depth markdown guides and schemas in `references/` (no scripts needed).
- **Examples**: `brand-guidelines`, `security-checklist`, `api-spec-reviewer`.

---

## 4. Capabilities-Based (`capabilities`)
- **Best for**: Complex integrated multi-module systems combining multiple modes of operation.
- **Frontmatter Declaration**:
  ```yaml
  metadata:
    pattern: capabilities
  ```
- **Workflow Section Focus**: Mode identification, composite script execution (`--mode`), and multi-artifact output verification.
- **Bundled Resources**: Multi-mode scripts in `scripts/`, domain specs in `references/`, boilerplates in `assets/`.
- **Examples**: `mcp-builder`, `artifacts-builder`.

