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

### `description` Field
- Write in **third-person** perspective ("This skill should be used when...").
- Keep under 500 characters / ~100 words.
- Explicitly state trigger scenarios, file types, and task goals.
- Avoid angle brackets (`<` or `>`).
