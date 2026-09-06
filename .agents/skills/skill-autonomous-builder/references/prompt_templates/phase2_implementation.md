# Phase 2: 3層リソース実装プロンプト

あなたは Google 『Agent Skills』ホワイトペーパー（May 2026）に準拠したスキル実装スペシャリストです。

### 目的
スキル `{SKILL_NAME}` の `tests/{SKILL_NAME}.test.json` に先行定義された仕様を 100% 満たすよう、`src/skills/{SKILL_NAME}/SKILL.md` および `scripts/` を実装してください。

### 対象スキル要求
* **スキル名**: `{SKILL_NAME}` (kebab-case)
* **目的・要件**:
```
{SKILL_DESCRIPTION}
```

---

### 手順

1. **先行テストケースの精読**:
   - `src/skills/{SKILL_NAME}/tests/{SKILL_NAME}.test.json` を開き、期待される入力、スクリプト名、引数（`positional_args` / `args`）、出力仕様を確認してください。
2. **決定論的スクリプトの実装 (`scripts/`)**:
   - **Shift Intelligence Left**: 業務ロジックや変換・解析処理は Python スクリプトに実装してください。
   - **汎用多段パイプライン設計 (Rationale & Architecture)**:
     - アルゴリズムは「① 入力パース ➔ ② 内部データ構造化 ➔ ③ レンダリング」の 3 段階で構成してください。
     - 特定のテストケース文字列（入力や期待値）に結合したハードコード比較（`if text == "..."`）は避け、未知の入力や動的な摂動にも耐える抽象化されたロジックを組んでください（実運用や CI の摂動テストで即座に破綻することを防ぐためです）。
   - スクリプト名は `snake_case`（例: `{PRIMARY_SCRIPT}.py`）とします。
   - 外部ライブラリを多用せず可能な限り標準ライブラリ（Zero-dependency）で完結させてください。外部パッケージが必要な場合は `argparse` で `--help` に対応させてください。
   - スクリプト単体で直接実行（`python scripts/{PRIMARY_SCRIPT}.py --help`）して正常動作することを確認してください。
3. **`SKILL.md` の実装**:
   - **テンプレートの完全具体化**:
     - `{task}` や `{skill_name}`、`<TODO>` などのプレースホルダーは一切残さず、すべて具体的かつ現実的な記述に置き換えてください（`edd validate` の決定論的ゲートで弾かれます）。
   - **Frontmatter**:
     - `name`: ディレクトリ名と完全一致する `kebab-case`
     - `description`: 動詞起点 ＋ Use when ＋ Do NOT use（50〜100 words）
     - `allowed-tools`: `run_skill_script load_skill_resource`
     - `metadata.pattern`: `workflow` または `task_based`
   - **白書 6大必須セクション**:
     - `## When to use`
     - `## When NOT to use`
     - `## Workflow` (CLI実行コマンド明記)
     - `## Examples` (Few-shot 入出力例)
     - `## Output format` (会話フィラー排除の指示)
     - `## Anti-patterns to avoid`
4. **静的検証 (Static Linter)**:
   - ターミナルで `edd validate {SKILL_NAME}` を実行してください。
   - エラー・警告が 0 件になるまで修正してください。
5. **Git コミット**:
   - `git add` および `git commit` を実行してください：
     ```bash
     git commit -m "feat({SKILL_NAME}): 3層リソースおよび SKILL.md の初版実装"
     ```
6. コミット完了を報告して本セッションを終了してください。
