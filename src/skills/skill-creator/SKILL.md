---
name: skill-creator
description: This skill should be used when users want to create new skills or redesign existing skills following the Anthropic Markdown-First and Progressive Disclosure (scripts, references, assets) standard.
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Creator

## Overview

Anthropic 公式標準および Google ADK 2.0 の Progressive Disclosure（3層リソース分離: `scripts/`, `references/`, `assets/`）に準拠した高品質なスキルパッケージを対話的・段階的に設計・構築するメタスキル。

## Workflow Decision Tree

スキル開発要件に応じて、以下の決定ロジックに従って開発を進行する：

- **If** 新規スキルの作成要件が与えられた場合 ➔ **Then** Step 1 で論理設計を行い、`scripts/init_skill.py` で雛形を生成後、リソースを実装して `scripts/quick_validate.py` で静的検証する
- **If** 既存スキルの改修・拡張の場合 ➔ **Then** 既存の `SKILL.md` および `references/` を精査し、必要な差分を適用して静的検証を行う
- **If** スキルの配布・エクスポートを求められた場合 ➔ **Then** `scripts/package_skill.py` を実行して検証済み ZIP アーカイブを出力する

## Step-by-Step Instructions

### Step 1: 要件分解と論理設計の策定
ユーザーの要求を分析し、以下の要素を策定する（詳細仕様は `references/skill_design_guide.md` を参照）：
1. **パターン分類**: `workflow`（順次決定木型）、`task_based`（ツール群型）、`reference`（仕様・知識型）、`capabilities`（複合型）から最適構成を選択する。
2. **トリガー具体例**: ユーザーが実際に発話するトリガープロンプト（3〜5例）を明確にする。
3. **意思決定ツリー**: 条件分岐（`If condition ➔ Then action`）を定義する。
4. **3層リソース計画**: 決定論的処理（`scripts/`）、知識資料（`references/`）、出力用テンプレート（`assets/`）に分解する。

### Step 2: スキル雛形の生成 *(Tool: `edd init` または `scripts/init_skill.py`)*
To initialize the skill scaffold directory and base files, execute:
```bash
# 統合 CLI を使用する場合
edd init <skill-name> --pattern workflow --path src/skills

# スタンドアロンスクリプトを実行する場合
python scripts/init_skill.py <skill-name> --pattern workflow --path src/skills
```

### Step 3: リソースの実装と SKILL.md の執筆
1. `references/skill_design_guide.md` の規約に従い、`SKILL.md` の Frontmatter（`name`, `description`）および手順書を客観的動詞起点（Imperative form）で執筆する。
2. 計画されたスクリプトを `scripts/` に配置する（`argparse` による `--help` 対応、余計な多層ラッパーを作らないフラットな実装）。
3. 知識資料を `references/`、テンプレート素材を `assets/` に配置する（不要な空ディレクトリは残さない）。

### Step 4: 高速静的検証 *(Tool: `edd validate` または `scripts/quick_validate.py`)*
To validate the structure, frontmatter, resource references, and naming conventions, execute:
```bash
# 統合 CLI を使用する場合 (AST解析付き高度検証)
edd validate src/skills/<skill-name>

# スタンドアロンスクリプトを実行する場合
python scripts/quick_validate.py src/skills/<skill-name>
```
エラーまたは警告が検知された場合は、指摘に従って `SKILL.md` や各リソースファイルを修正する。

### Step 5: 配布用 ZIP パッケージ化 *(Tool: `edd package` または `scripts/package_skill.py`)*
To package and export the validated skill for distribution (Claude Code, Antigravity, Cursor, ADK), execute:
```bash
# 統合 CLI を使用する場合
edd package src/skills/<skill-name> --out dist

# スタンドアロンスクリプトを実行する場合
python scripts/package_skill.py src/skills/<skill-name> dist
```

## Usage Scenarios & Trigger Examples

- "新しいスキルとして、PDFを回転・結合する pdf-tools スキルを作成してください。"
- "既存の text-analyzer スキルに JSON 解析機能を追加・更新したい。"
- "作成したスキルを配布用 ZIP パッケージに固めて出力して。"

## When NOT to Use This Skill

- **単純なワンライナーのコード生成や一回限りのスクリプト実行**: スキルパッケージを作成する必要がない単発タスクには使用しない。
- **既存のテストスイートの実行・診断のみを目的とする場合**: スキル生成ではなく、`skill-evaluator` または `skill-diagnoser` を直接使用する。
- **既存スキルの自動修復ループ実行**: `skill-optimizer` を使用する。

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/init_skill.py`**: スキル雛形を高速生成する決定論的初期化CLIツール
- **`scripts/quick_validate.py`**: Frontmatter・実在参照・規約を高速検査するバリデータ
- **`scripts/package_skill.py`**: スキルを静的検証した上で配布用 ZIP パッケージを出力する決定論的CLIツール

### `references/` (On-Demand Knowledge)
- **`references/skill_design_guide.md`**: スキル設計原則、パターン選定基準、3層リソース分離のガイドライン

## Guidelines & Best Practices

- 既存スキルのインベントリを必ず照合し、重複作成を避けて既存スキルの拡張（Update）を優先すること。
- 生成・更新したスキルは必ず `scripts/quick_validate.py` で検証をパスさせること。
- スクリプトは外部非標準ライブラリへの依存を極力排除し、決定論的ブラックボックスツールとして設計すること。
- 未使用の空ディレクトリ（`assets/` や `references/` 等）は残置しないこと。
