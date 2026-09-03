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
1. 要件ヒアリングと具体例の明確化 (Understanding with Concrete Examples):
   - 一度に多すぎる質問をせず、最も重要な質問から順に確認する：
     - 「このスキルがサポートすべき具体的機能は何か？」
     - 「ユーザーが何と発話した時にこのスキルをトリガーすべきか？（正例発話3件）」
     - 「逆に、類似しているがこのスキルをトリガーしてはならない境界ケースは何か？（負例境界3件）」
   - スキルの構造パターン（workflow, task_based, reference, capabilities）を選択する。

2. 再利用可能リソースの峻別計画 (Resource Planning):
   - `scripts/`: 決定論的信頼性が必要な処理、繰り返し書き直されるコード、計算・フォーマット変換
   - `references/`: ドメイン固有のスキーマ、API仕様、業務規約（SKILL.md を5,000語以下にスリムに保つ）
   - `assets/`: 成果物生成用のテンプレート、ボイラープレート、画像等の静的ファイル（コンテキストに読ませない）

3. インバージョン開発 (EDD Inversion) による評価セット先行策定 (SSOT):
   - SKILL.md を執筆する前に、まず `tests/<skill-name>_edd.evalset.json` に Google ADK 2.0 公式 `EvalSet` 形式で **3つの正例 ＋ 3つの負例（計6ケース）** を確定する。
   - `tests/test_config.json` にて ADK 公式 `EvalConfig`（`tool_trajectory_avg_score: match_type: IN_ORDER`, `rubric_based_final_response_quality_v1`）を定義し、Progressive Disclosure を行うエージェントを公平に評価できるようにする。
   - ツール呼び出し・引数検証は `intermediate_data.tool_uses`（Trajectory レイヤー）に集約し、`rubric` は最終出力品質（会話フィラー排除・正確性・負例時の沈黙）に特化させる。

4. スキル雛形の生成 (Scaffold):
   - 統合 CLI `edd init` を呼び出してパッケージ雛形（`SKILL.md`, `scripts/`, `tests/*_edd.evalset.json`, `tests/test_config.json`）を一括初期化する。
     ```bash
     edd init <skill-name> --pattern workflow --path src/skills
     ```

5. SKILL.md の執筆とリソースの実装:
   - 白書 Appendix A minimal SKILL.md 6大必須セクションを客観的・命令的文体（"To accomplish X, do Y"）で執筆する。
   - 過度な大文字強調（`ALWAYS`, `NEVER` 等）を排除し、理由（Rationale）を説明して Context Debt を防ぐ。
   - 外部連携は MCP ツールに委譲し、スクリプト内で巨大な HTTP クライアントを再発明しない。

6. 高速静的検証 (Validation):
   - `edd validate` を実行して AST 解析、リソース実在性、および 3正例＋3負例の整合性を検証する。
     ```bash
     edd validate src/skills/<skill-name>
     ```

7. 配布用 ZIP パッケージ化 (Packaging):
   - 検証済みスキルを ZIP パッケージとして出力する。
     ```bash
     edd package src/skills/<skill-name> --out dist
     ```

## Examples
- Input: "Create a new workflow skill for processing PDF invoices" → Output: "Scaffolded and validated 'processing-pdf-invoices' skill with 6 EDD eval cases"
- Input: "Harvest skill from execution trace trace.json" → Output: "Generated skill package under src/skills/"

## Output format
- 生成・更新されたスキルディレクトリ構造、各ファイルパス、および `edd validate` の検証結果サマリーを提示する。

## Anti-patterns to avoid
- インベントリ（既存スキル）を確認せずに重複スキルを新規作成しないこと。
- スクリプト内部で巨大な HTTP クライアントを再発明しないこと（外部連携は MCP に委譲する）。
- 未使用の空ディレクトリ（空の assets/ や references/）を残置しないこと。
- Google ADK 2.0 公式 `EvalSet` 形式の評価データセット（tests/）の作成を省略しないこと。
- 「ALWAYS DO X」のような大文字命令を乱用して Context Debt を蓄積させないこと（理由を説明するか決定論的スクリプトに落とし込む）。
- 6大必須セクション（When to use, When NOT to use, Workflow, Examples, Output format, Anti-patterns to avoid）を省略しないこと。

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
