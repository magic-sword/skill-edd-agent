---
name: skill-creator
description: "新しいスキルの自動生成または既存スキルの再設計を行うメタスキル。Markdown-First アーキテクチャおよび Progressive Disclosure（3層リソース分離）原則に準拠した高品質な SKILL.md、scripts/、references/、assets/ を自律的に設計・出力する。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Creator

## Overview

自然言語の要件や既存のコードベースから、Anthropic公式標準の Markdown-First アーキテクチャと Progressive Disclosure（3層リソース分離）に準拠した高品質なスキルパッケージを自動生成・再設計するメタスキル。

## Workflow Decision Tree

スキル開発要件に応じて、以下の決定ロジックに従って生成パイプラインを実行する：

- **If** 新規スキル要件が自然言語で提供された場合 ➔ **Then** `scripts/creator.py` を呼び出し、Stage 1（論理設計抽出）から Stage 3（静的検証・自己修復）を一括実行して完全なスキルを生成する
- **If** 既存スキルの改修・再設計の場合 ➔ **Then** 既存の `SKILL.md` およびリソースを解析し、差分を反映して再生成する

## Step-by-Step Instructions

### Step 1: 思考の構造化と具体例分析 *(Target: `scripts/creator.py`)*

ユーザー要件から以下の論理設計要素（`SkillLogicDraft`）を構造化抽出する：
1. **パターン分類**: `workflow`, `task_based`, `reference`, `capabilities` の4大パターンから最適構成を選択する。
2. **トリガー具体例**: ユーザーが実際に発話するトリガーシナリオ（3〜5例）を洗い出す。
3. **意思決定ツリー**: 状況別の条件分岐ロジック（`If condition ➔ Then action`）を策定する。
4. **3層リソース計画**: 決定論的処理（`scripts/`）、知識資料（`references/`）、出力用テンプレート（`assets/`）にタスクを分解する。

### Step 2: 決定論的 Markdown レンダリング *(Target: `scripts/creator.py`)*

`SkillTemplateEngine` を用いて、Frontmatter、標準見出し階層、意思決定ツリー、リソース案内、ガイドラインを含む `SKILL.md` をプログラムで決定論的に組み立てる。

### Step 3: 3層リソースの生成と配置 *(Target: `scripts/creator.py`)*

計画された各リソースファイル（Python/Bashスクリプト、参照Markdown、テンプレート素材）の実装コード・ドキュメントを生成し、適切なディレクトリ（`scripts/`, `references/`, `assets/`）に配置する。

### Step 4: 静的検証と自己修復ループ *(Target: `scripts/creator.py`)*

`SkillValidator` を実行して Frontmatter 構文、リソース実在整合性、CLIハーネス（`argparse` / `--help` / エントリポイント）、Imperative 文体を検査する。エラーや警告が検知された場合は、LLMへの差分フィードバックにより最大3回まで自動修正（Self-Correction）を実行する。

### Step 5: スキル配布用パッケージング *(Target: `scripts/package_skill.py`)*

完成したスキルを外部配布（Claude Code, Antigravity, Cursor 等）する場合、`scripts/package_skill.py <skill_dir> --output <out_dir>` を実行して静的検証済み ZIP アーカイブを出力する。

## Usage Scenarios & Trigger Examples

このスキルは以下のようなリクエストでトリガーされる：

- "新しいスキルとして、PDFを回転・結合する pdf-tools スキルを作成してください。"
- "APIクライアントを自動生成するワークフロー型のスキルを設計・構築したい。"
- "作成したスキルを配布用 ZIP パッケージに固めて出力して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/creator.py`**: 4段階品質保証パイプラインを実行するコア自動生成エンジン（CLI対応）
- **`scripts/package_skill.py`**: スキルを静的検証した上で配布用 ZIP パッケージを出力する決定論的CLIツール
- **`scripts/main.py`**: CLIおよびエージェント向け公開関数（`create_skill`）のエントリポイント

### `references/` (On-Demand Knowledge)
- **`references/skill_design_guide.md`**: スキル設計原則、パターン選定基準、3層リソース分離のガイドライン

### `assets/` (Output Templates & Boilerplates)
- **`assets/prompts/draft_extraction.txt`**: Stage 1 論理設計抽出プロンプトテンプレート
- **`assets/prompts/resource_generation.txt`**: Stage 3 リソース生成プロンプトテンプレート
- **`assets/template_sample.txt`**: スキル出力用のボイラープレートテンプレート

## Guidelines & Best Practices

- すべての生成物は必ず `SkillValidator` の静的チェック（AST CLI検査、空ディレクトリ検知）をパスさせること。
- `scripts/` に配置するPythonスクリプトは、冗長なラッパーを作らずフラットで簡潔な実装とし、必ず `argparse`（`--help`）および `if __name__ == '__main__':` を備えた決定論的ブラックボックスツールとすること。
- ドキュメント参照だけで解決するタスクには無理にPythonスクリプトを生成せず、`references/` を活用すること。
- 未使用の空ディレクトリ（`assets/` や `references/` 等）は作成・残置せず、リソース計画に存在するディレクトリのみを配置すること。


