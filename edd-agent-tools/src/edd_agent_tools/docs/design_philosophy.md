# Agent Skill 設計思想 (Design Philosophy)

本プロジェクトにおける Google ADK 2.0 および Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの設計思想とベストプラクティスを記録します。

---

## 1. コア思想

### ① 単一真実源の原則 (Single Source of Truth ➔ Markdown-First)
* 仕様書兼プロンプトである **`SKILL.md` を唯一の真実源** とし、自然言語（Markdown）とコード（Python）のシームレスな統合を図ります。

### ② Progressive Disclosure（3層リソース分離）
* コンテキストウィンドウの効率化と信頼性の両立を図るため、スキル資産を3層に分離します：
  1. **Level 1: YAML Frontmatter**（常時ロード: `name`, `description`）
  2. **Level 2: SKILL.md 本文**（トリガー時ロード: 意思決定ツリー、手順、ガイドライン）
  3. **Level 3: 3層リソース**（オンデマンド実行・ロード）
     - `scripts/`: 決定論的Python/Bashスクリプト
     - `references/`: ドメイン知識・API仕様・スキーマ
     - `assets/`: 出力用テンプレート・素材

### ④ Google ADK 2.0 ネイティブ統合 (`SkillToolset`)
* 全スキルの Python 関数を直接 `FunctionTool` として一括展開するアンチパターン（Context Bloat）を排除し、Google ADK 2.0 標準の `SkillToolset` による Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `load_skill_resource` ➔ `run_skill_script`）を採用。
* エージェント起動時のコンテキスト消費を極小化しつつ、決定論的スクリプトのブラックボックス実行と安全なパス解決を実現。

### ⑤ スキルのポータビリティと Zero-dependency CLI ツール群
* 各スキルは単体で外部プラットフォーム（Claude Code, Antigravity, Cursor 等）へドロップイン可能な自己完結性を持つ。
* `skill-creator` 配下に外部依存不要（標準ライブラリのみ）で動作する `quick_validate.py`, `init_skill.py`, `package_skill.py` を同梱し、環境を選ばない即時検証・パッケージングを実現。

---

## 2. フォルダ構造の規約 (3-Tier Layout)

```
src/skills/{skill-name}/
  SKILL.md       # YAML Frontmatter ('This skill should be used when...') + Markdown仕様書 (SSOT)
  scripts/       # 決定論的スクリプト（直接実行可能・CLI対応）
    main.py
  references/    # ドメイン知識・仕様・スキーマ（オンデマンド参照）
    guide.md
  assets/        # 出力用テンプレート・素材
    template.txt
```
