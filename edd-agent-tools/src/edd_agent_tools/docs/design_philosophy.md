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

### ③ 4段階品質保証パイプライン (Stage-Gate)
* **Stage 1 (Logical Structuring)**: 要件から論理設計（`SkillLogicDraft`）を構造化抽出。
* **Stage 2 (Deterministic Rendering)**: `SkillTemplateEngine` による決定論的 SKILL.md 生成。
* **Stage 3 (Resource Infilling)**: 3層リソースの生成・配置。
* **Stage 4 (Static Validation & Self-Correction)**: `SkillValidator` による構文・整合性検査と自己修復。

---

## 2. フォルダ構造の規約 (3-Tier Layout)

```
src/skills/{skill-name}/
  SKILL.md       # YAML Frontmatter + Markdown仕様書 (SSOT)
  scripts/       # 決定論的スクリプト（直接実行可能）
    main.py
  references/    # ドメイン知識・仕様・スキーマ（オンデマンド参照）
    guide.md
  assets/        # 出力用テンプレート・素材
    template.txt
```
