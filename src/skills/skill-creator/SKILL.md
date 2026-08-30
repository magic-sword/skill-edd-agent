---
name: skill-creator
description: This skill should be used when users want to create new skills or redesign existing skills following the Anthropic Markdown-First and Google ADK 2.0 Progressive Disclosure (scripts, references, assets) standard.
license: MIT
pattern: workflow
---

# Skill Creator

## Overview

Anthropic 公式標準および Google ADK 2.0 の Progressive Disclosure（3層リソース分離: `scripts/`, `references/`, `assets/`）に準拠した高品質なスキルパッケージを対話的・段階的に設計・構築するメタスキル。

## Workflow Decision Tree

スキル開発要件に応じて、以下の決定ロジックに従って開発を進行する：

- **If** 新規スキルの作成要件が与えられた場合 ➔ **Then** Step 1 で具体例と論理設計を策定し、`scripts/init_skill.py` で雛形生成後、`assets/templates/` を参考に `SKILL.md` とリソースを実装して `scripts/quick_validate.py` で静的検証する
- **If** 既存スキルの改修・拡張の場合 ➔ **Then** 既存の `SKILL.md` および `references/` を精査し、必要な差分を適用して静的検証を行う
- **If** スキルの配布・エクスポートを求められた場合 ➔ **Then** `scripts/package_skill.py` を実行して検証済み ZIP アーカイブを出力する

## Step-by-Step Instructions

### Step 1: 要件ヒアリングと具体例の明確化 (Concrete Examples)
ユーザーの要求を分析し、以下の要素を策定する（詳細仕様は `references/skill_design_guide.md` を参照）：
1. **具体例の特定**: ユーザーが実際に発話するトリガープロンプト（3〜5例）と期待される入出力を明確にする。
2. **パターン分類**: `workflow`（順次決定木型）、`task_based`（ツール群型）、`reference`（仕様・知識型）、`capabilities`（複合型）から最適構成を選択する。
3. **3層リソース計画**:
   - `scripts/`: 決定論的CLIツール（Python 標準ライブラリ、`argparse` 対応）
   - `references/`: ドメイン仕様書・スキーマ（オンデマンド参照）
   - `assets/`: 出力用テンプレート素材（ボイラープレート等）
   - `tests/`: 契約テストおよびトリガー評価ケース（`*.evalset.json`）

### Step 2: スキル雛形の生成 *(Tool: `edd init` または `scripts/init_skill.py`)*
To initialize the skill scaffold directory and base files, execute:
```bash
# 統合 CLI を使用する場合
edd init <skill-name> --pattern workflow --path src/skills

# スタンドアロンスクリプトを実行する場合
python scripts/init_skill.py <skill-name> --pattern workflow --path src/skills
```

### Step 3: リソースの実装と SKILL.md の執筆
1. `assets/templates/` 配下の Markdown テンプレート素材（`workflow_template.md`, `task_based_template.md`, `reference_template.md`, `capabilities_template.md` 等）を参考に、`SKILL.md` の Frontmatter（`name`, `description`）および手順書を客観的動詞起点（Imperative form）で執筆する。
2. 計画されたスクリプトを `scripts/` に配置する（`argparse` による `--help` 対応、余計な多層ラッパーを作らないフラットな実装）。
3. 知識資料を `references/`、テンプレート素材を `assets/`、テストケースを `tests/` に配置する（不要な空ディレクトリは残さない）。

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

Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):
- **粒度境界 (Granularity)**: 単純なワンライナーのシェルコマンドや一回限りのコードスニペット生成など、再利用可能なスキルパッケージを作成する必要がない軽微なタスク。
- **技術的限界 (Out-of-Scope)**: 対象ドメインの業務処理（ケース変換、PDF編集、データ抽出など）自体の実行。生成された個別スキルを直接利用すること。
- **ライフサイクル分離 (Lifecycle)**: 既存スキルの評価テスト実行、失敗原因の診断、自律的自己修復、および Tier 昇格判定（`skill-evolver` を使用すること）。
- **インベントリ照合 (Inventory)**: 類似の機能やスコープを持つスキルが既に `SkillsState` / `src/skills/` に存在する場合（重複作成を避け、既存スキルの改修・拡張を優先すること）。

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/init_skill.py`**: スキル雛形を高速生成する決定論的初期化CLIツール
- **`scripts/quick_validate.py`**: Frontmatter・実在参照・規約を高速検査するバリデータ
- **`scripts/package_skill.py`**: スキルを静的検証した上で配布用 ZIP パッケージを出力する決定論的CLIツール

### `references/` (On-Demand Knowledge)
- **`references/skill_design_guide.md`**: スキル設計原則、パターン選定基準、3層リソース分離のガイドライン

### `assets/` (Output Templates & Boilerplates)
- **`assets/templates/`**: 各スキルパターン用（workflow, task_based, reference, capabilities）の Markdown テンプレート素材集

## Guidelines & Best Practices

- 既存スキルのインベントリを必ず照合し、重複作成を避けて既存スキルの拡張（Update）を優先すること。
- 生成・更新したスキルは必ず `scripts/quick_validate.py` または `edd validate` で検証をパスさせること。
- スクリプトは外部非標準ライブラリへの依存を極力排除し、決定論的ブラックボックスツールとして設計すること。
- 未使用の空ディレクトリは残置しないこと。
