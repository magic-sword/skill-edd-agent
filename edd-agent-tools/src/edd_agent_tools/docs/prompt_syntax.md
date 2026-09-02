# Prompt Syntax & Imperative Writing Guidelines

## 1. Imperative / Verb-First Form
All instructions in `SKILL.md` and agent prompts must use **imperative/infinitive form** (verb-first instructions), not second-person or conversational phrasing.

- ❌ **Avoid Conversational Phrasing**:
  - "〜してください" (Please do ...)
  - "〜する必要があります" (It is necessary to ...)
  - "You should execute scripts/foo.py"
- ⭕️ **Use Direct Action Directives**:
  - "To perform X, execute `scripts/foo.py` with `--input <path>`."
  - "X を実行するには、`scripts/foo.py` を `--input <path>` で呼び出す。"
  - "Verify prerequisites before proceeding to Step 2."

---

## 2. YAML Frontmatter Guidelines

### `name` Field
- Lowercase hyphen-case only (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Must match the directory name.
- Example: `pdf-tools`, `git-conflict-resolver`.

### `description` Field (Routing Algorithm)
- Treat the description as the agent's routing algorithm.
- Structure with 3 key components (~50-100 words, ≤1024 chars):
  1. **Verb-led purpose sentence**: Describe what it does starting with an active verb (e.g., "Converts text between case styles...").
  2. **Trigger conditions**: Explicitly state when to trigger (e.g., "Use when the user asks to..."). Front-load trigger keywords.
  3. **Anti-trigger / Bounds**: Explicitly state when NOT to trigger (e.g., "Do NOT use for...").
- Avoid vague phrases (e.g., "A helpful skill for", "Helps with").
- Avoid angle brackets (`<` or `>`).
