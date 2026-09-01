# Progressive Disclosure & 3-Tier Resource Architecture

## 1. Core Principle
Skills use a three-level loading system to optimize context window efficiency for AI agents:

1. **Level 1: Metadata (YAML Frontmatter)**
   - Always in context (~100 words).
   - Contains `name` (lowercase hyphen-case) and `description` (third-person trigger explanation).

2. **Level 2: SKILL.md Body**
   - Loaded into context only when the skill triggers (<5k words).
   - Contains Overview, Workflow Decision Tree / Available Tasks, Step-by-Step Instructions, Usage Scenarios, `When NOT to Use This Skill` (Negative Space Guidance), and Guidelines.

3. **Level 3: Bundled Resources**
   - Loaded or executed on demand (Unlimited capacity).
   - Separated into specialized directories: `scripts/`, `references/`, `assets/`, `examples/`, and `tests/`.

---

## 2. Resource Directory Separation

### `scripts/` (Executable Tools - Black-box Execution)
- **Purpose**: Deterministic Python/Bash scripts for tasks requiring exact reliability or automation.
- **Rule**: Must support `--help` CLI parsing (`argparse`/`sys`). Agents must execute with `--help` first to inspect arguments and avoid cluttering context window with raw source code.

### `references/` (On-Demand Knowledge)
- **Purpose**: In-depth API specifications, database schemas, domain knowledge, and comprehensive policies.
- **Rule**: Loaded into context only when the agent explicitly determines reference material is required. Keep `SKILL.md` lean by moving details here.

### `assets/` (Output Templates & Boilerplates)
- **Purpose**: Template files, boilerplates, HTML/React project skeletons, icons, fonts, and assets meant to be copied or used in final outputs.
- **Rule**: Not intended to be read into reasoning context; instead copied or served directly.

### `examples/` (Usage Patterns & Concrete Demonstrations)
- **Purpose**: Concrete code snippets, sample invocation patterns, and typical configurations for agents to emulate.
- **Rule**: Loaded on demand when the agent needs guidance on implementation style or parameter formatting.

---

## 3. Standard Operational Patterns

1. **Reconnaissance-then-Action**: Always inspect inputs, DOM, or file structures first before performing modifications.
2. **Minimal Edits & Batching**: Make targeted, minimal edits preserving RSIDs, formatting, and surrounding context. Batch large changes into manageable chunks (3-10 edits).
3. **Negative Guidance (When NOT to use)**: Explicitly scope out-of-boundary tasks across Granularity, Out-of-Scope, Lifecycle, and Inventory.
