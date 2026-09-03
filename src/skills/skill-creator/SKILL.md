---
name: skill-creator
description: |
  Creates and scaffolds new agent skills or redesigns existing skills following Anthropic Markdown-First and Google ADK 2.0 Progressive Disclosure standards.
  Use when the user asks to author a skill, scaffold a skill package, extract skills from execution traces, or export distributable skill ZIP packages.
  Do NOT use for skill evaluation, regression diagnosis, self-healing loops, or tier promotion (use skill-evolver).
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: workflow
---

# Skill Creator

## When to use
- 新しいスキル（例: pdf-tools, docx-extractor 等）の設計・雛形作成を求められた時
- 過去の実行ログや会話トレース（trace.json）からスキルを自律抽出・作成したい時
- 既存スキルの Markdown 仕様やリソースを改修・拡張したい時
- 作成・検証済みのスキルを配布用 ZIP パッケージとしてエクスポートしたい時

## When NOT to use
- 単純なワンライナーコマンドや一時的なコードスニペットの生成で完結するタスク
- 対象ドメインの業務処理（ケース変換やファイル解析など）自体の実行
- スキルの多層評価テスト実行、失敗診断、自己修復、Tier 昇格（`skill-evolver` を使用すること）
- Python パッケージ全体のビルド・リリース作業

## Workflow
1. 要件ヒアリングと具体例の明確化: 発話プロンプト（正例・負例）と入出力を特定し、4大パターン（workflow, task_based, reference, capabilities）を選択する。
2. スキル雛形の生成: `edd init` または `edd harvest-trace` を呼び出してパッケージ雛形を初期化する。
   ```bash
   edd init <skill-name> --pattern workflow --path src/skills
   ```
3. インバージョン開発 (EDD Inversion) による評価ケース先行策定: `tests/<skill-name>_edd.evalset.json` に白書 Snippet 3 形式評価ケースを先行定義する。
4. リソースの実装と SKILL.md の執筆: テンプレートを参考に、Frontmatter および白書 6 大必須セクションを客観的指示（Imperative form）で執筆し、必要なリソース（`scripts/`, `references/`, `assets/`, `examples/`）を配置する。
5. 高速静的検証: `edd validate` を実行して AST 解析およびリソース整合性を検証する。
   ```bash
   edd validate src/skills/<skill-name>
   ```
6. 配布用 ZIP パッケージ化: 検証済みスキルを ZIP パッケージとして出力する。
   ```bash
   edd package src/skills/<skill-name> --out dist
   ```

## Examples
- Input: "Create a new workflow skill for processing PDF invoices" → Output: "Scaffolded and validated 'processing-pdf-invoices' skill"
- Input: "Harvest skill from execution trace trace.json" → Output: "Generated skill package under src/skills/"

## Output format
- 生成・更新されたスキルディレクトリ構造、各ファイルパス、および `edd validate` の検証結果サマリーを提示する。

## Anti-patterns to avoid
- インベントリ（既存スキル）を確認せずに重複スキルを新規作成しないこと。
- スクリプト内部で巨大な HTTP クライアントを再発明しないこと（外部連携は MCP に委譲する）。
- 未使用の空ディレクトリ（空の assets/ や references/）を残置しないこと。
- 白書 Snippet 3 形式の評価データセット（tests/）の作成を省略しないこと。

## Requirements & Prerequisites
本スキルは EDD エコシステム公式のメタスキルであり、以下の前提環境で動作します：
- **Python**: >= 3.11
- **Package**: `pip install -e edd-agent-tools` (または `pip install edd-agent-tools`)
- **CLI**: `edd` コマンドが環境パスに解決可能であること

## Bundled Resources
### `references/` (On-Demand Knowledge)
- **`references/skill_design_guide.md`**: スキル設計原則、パターン選定基準、3層リソース分離のガイドライン。

### `assets/` (Output Templates & Boilerplates)
- **`assets/templates/`**: 各スキルパターン用（workflow, task_based, reference, capabilities）の Markdown テンプレート素材集。
