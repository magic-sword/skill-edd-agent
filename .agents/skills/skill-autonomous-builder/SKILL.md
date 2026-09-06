---
name: skill-autonomous-builder
description: |
  Autonomously builds, evaluates, self-heals, and promotes new or upgraded agent skills through ephemeral Antigravity CLI (agy) sessions.
  Use when the user or agent needs to create a new skill from a description or trace, following Google Agent Skills whitepaper (May 2026) EDD inversion and 3-Tier quality ladder.
  Do NOT use for ad-hoc manual single-file edits or simple command execution.
license: MIT
allowed-tools: run_command view_file
metadata:
  pattern: workflow
---

# Skill Autonomous Builder (Self-Evolving Skills Loop)

## When to use
- 自然言語の要求（「○○を自動化するスキルを作って」「△△を変換・解析するスキルを構築して」）から、Google 『Agent Skills』ホワイトペーパー（May 2026）完全準拠のスキルを自律構築したい時
- EDD（Evaluation-Driven Development）インバージョン開発に従い、3正例＋3負例のテストケース先行定義から実装・評価までを自動化したい時
- コンテキスト汚染（Context Rot）を回避し、フェーズごとに独立したクリーンセッション（Ephemeral Sessions）でスキルを構築・自己修復したい時
- 新規スキルを多層評価テストに合格させ、Tier 1〜3（Read-Only, Draft-Only, Action-Allowed）へ安全に昇格させたい時

## When NOT to use
- 既存の `SKILL.md` や Python スクリプトに対する単発の 1 行手動修正
- 単純な `pytest` コマンドの手動実行
- プロジェクト本体（`edd-agent-tools` パッケージ）の ADK 最適化（`adk-optimizer` を使用すること）

## Workflow
1. **要求の明確化**:
   - 構築したいスキル名（`kebab-case`）および機能要求・入出力を定義する。
2. **自律構築ループの起動**:
   - `scripts/run_builder_loop.py` を実行する。
   ```bash
   # デフォルト (Tier 1 目標)
   python3 .agents/skills/skill-autonomous-builder/scripts/run_builder_loop.py \
     --skill-name <skill-name> \
     --description "<スキルの要求仕様・機能目的>"

   # Tier 2 (Draft-Only) 目標で構築
   python3 .agents/skills/skill-autonomous-builder/scripts/run_builder_loop.py \
     --skill-name <skill-name> \
     --description "<スキルの要求仕様>" \
     --target-tier 2

   # 事前検証 (Dry-run)
   python3 .agents/skills/skill-autonomous-builder/scripts/run_builder_loop.py \
     --skill-name <skill-name> \
     --description "<要求>" \
     --dry-run
   ```
3. **自律ライフサイクル（4大フェーズの進行監視）**:
   - 各フェーズが独立したクリーンな `agy` CLI プロセスとして実行される：
     - **Phase 1 (EDD Inversion)**: `tests/{skill}.test.json`（3正例＋3負例）および `test_config.json` を先行策定してコミット
     - **Phase 2 (Implementation)**: `SKILL.md`（6大セクション）および `scripts/`（決定論的Python）を実装し、`edd validate` 合格後にコミット
     - **Phase 3 (Eval & Heal)**: `edd eval --pass-k 3` を実行し、失敗時は `edd diagnose` で自己修復を反復してコミット
     - **Phase 4 (Cascade & Promote)**: 連鎖回帰テスト（Cascade Testing）を実行し、目標 Tier への昇格を確定して `BUILDER_COMPLETE` を出力

## Examples
- Input: "PDFから表データを抽出してMarkdownに変換するスキル `pdf-table-extractor` を自律構築して"
  Output: "自律スキル構築ループを開始しました。進捗ログ: .skill_builder.log"
- Input: "run_builder_loop.py を dry-run で確認して"
  Output: "全4フェーズのプロンプト構成および変数置換を正常に検証しました"

## Output format
- 各フェーズのコミットハッシュ、テスト成否、および最終的な Tier 昇格結果ステータスを提示する。

## Anti-patterns to avoid
- テスト先行策定（EDD インバージョン）を省略していきなり `SKILL.md` を書き始めないこと。
- 単一セッションで全フェーズを一気に進めて Context Rot（コンテキスト劣化）を引き起こさないこと。
- 負例（発動してはならない境界ケース）を省略して誤爆（Over-trigger）の原因を作らないこと。
- 失敗したテストを推測で直さず、必ず `edd diagnose` の構造化診断ログに基づいてピンポイントに修復すること。

## Requirements & Prerequisites
- **Antigravity CLI (`agy`)**: バージョン 1.1.1 以上（`agy --version`）
- **Package**: `pip install -e edd-agent-tools`
- **CLI**: `edd` コマンドが環境パスで解決可能であること
- **Python**: >= 3.10

## Bundled Resources
### `references/`
- **`references/inversion_rules.md`**: 白書 Section 4 準拠の 3正例＋3負例先行策定規約
- **`references/evaluation_ladder.md`**: 白書 Section 4 準拠の 3-Tier 品質防壁昇格基準
### `references/prompt_templates/`
- 各フェーズ（Phase 1〜4）の独立セッション向けプロンプトテンプレート群
### `scripts/`
- **`scripts/run_builder_loop.py`**: 自律スキル構築ループの親オーケストレーター
