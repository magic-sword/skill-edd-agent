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
   - Separated into three distinct directories: `scripts/`, `references/`, and `assets/`.

---

## 2. 3-Tier Resource Separation

### `scripts/` (Executable Tools)
- **Purpose**: Deterministic Python/Bash scripts for tasks requiring exact reliability or automation.
- **Rule**: Can be executed directly in the environment without reading full source code into the agent's context window.

### `references/` (On-Demand Knowledge)
- **Purpose**: In-depth API specifications, database schemas, domain knowledge, and comprehensive policies.
- **Rule**: Loaded into context only when the agent explicitly determines reference material is required. Keep `SKILL.md` lean by moving details here.

### `assets/` (Output Templates & Boilerplates)
- **Purpose**: Template files, boilerplates, HTML/React project skeletons, icons, fonts, and assets meant to be copied or used in final outputs.
- **Rule**: Not intended to be read into reasoning context; instead copied or served directly.
