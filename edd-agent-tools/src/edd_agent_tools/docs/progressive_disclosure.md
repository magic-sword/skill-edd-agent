# Progressive Disclosure & 3-Tier Resource Architecture

## 1. Core Principle
Skills use a three-level loading system to optimize context window efficiency for AI agents:

1. **Level 1: Metadata (YAML Frontmatter)**
   - Always in context (~100 words).
   - Contains `name` (lowercase hyphen-case matching directory), `description` (third-person routing algorithm), and `allowed-tools` (space-delimited allowed tools, e.g. `run_skill_script load_skill_resource`).


2. **Level 2: SKILL.md Body (Whitepaper Appendix A Minimal SKILL.md Standard)**
   - Loaded into context only when the skill triggers (<5k words).
   - Structured into the 6 essential sections: `## When to use`, `## When NOT to use`, `## Workflow`, `## Examples`, `## Output format`, and `## Anti-patterns to avoid`.

3. **Level 3: Bundled Resources (Google ADK 2.0 Native 3-Tier Structure)**
   - Loaded or executed on demand (Unlimited capacity).
   - Separated into specialized directories: `scripts/`, `references/`, `assets/`, and `tests/` (`{skill_name}.test.json` as Single Source of Truth). Usage patterns and reference implementations are placed in `references/` or `assets/` to align with the Google ADK 2.0 `Resources` specification.

---

## 2. Resource Directory Separation (Google ADK 2.0 Pure Spec)

### `scripts/` (Executable Tools - Black-box Execution)
- **Purpose**: Deterministic Python/Bash scripts for tasks requiring exact reliability or automation.
- **Rule**: Must support `--help` CLI parsing (`argparse`/`sys`). Agents must execute with `--help` first to inspect arguments and avoid cluttering context window with raw source code.

### `references/` (On-Demand Knowledge & Usage Patterns)
- **Purpose**: In-depth API specifications, database schemas, domain knowledge, usage patterns, and reference implementations.
- **Rule**: Loaded into context only when the agent explicitly determines reference material is required. Keep `SKILL.md` lean by moving details here.

### `assets/` (Output Templates & Boilerplates)
- **Purpose**: Template files, boilerplates, HTML/React project skeletons, icons, fonts, sample data, and assets meant to be copied or used in final outputs.
- **Rule**: Not intended to be read into reasoning context; instead copied or served directly.

---

## 3. Standard Operational Patterns

1. **Reconnaissance-then-Action**: Always inspect inputs, DOM, or file structures first before performing modifications.
2. **Minimal Edits & Batching**: Make targeted, minimal edits preserving RSIDs, formatting, and surrounding context. Batch large changes into manageable chunks (3-10 edits).
3. **Negative Guidance (When NOT to use)**: Explicitly scope out-of-boundary tasks across Granularity, Out-of-Scope, Lifecycle, and Inventory.
