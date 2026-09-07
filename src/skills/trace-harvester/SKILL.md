---
name: trace-harvester
description: |
  Extracts and crystallizes reusable agent skills and deterministic workflows directly from execution traces or conversation transcripts.
  Use when the user asks to harvest skills from logs, turn execution traces into skills, or crystallize past successes into reusable procedural memory.
  Do NOT use for manual skill authoring from scratch (use skill-creator) or skill evaluation and healing (use skill-evolver).
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: workflow
---

# Trace Harvester

## When to use
- 過去のエージェント実行ログや会話セッション（`transcript.jsonl` や `trace.json`）から再利用可能なワークフローを発見し、自動的にスキル化したい時
- 成功した複数ステップのツール呼び出しシーケンスを決定論的手順書（`SKILL.md` + `scripts/`）として結晶化（Crystallize）したい時
- 手作業での手順執筆の手間を省き、実際の実行実績（Ground Truth）に基づいた初期スキルドラフトを生成したい時

## When NOT to use
- ゼロからの新規スキル要件定義・設計（`skill-creator` または `skill-autonomous-builder` を使用すること）
- スキルの多層評価テスト、失敗診断、自己修復、Tier 昇格（`skill-evolver` を使用すること）
- 個別のドメイン業務処理の実行

## Workflow
1. **トレースデータの特定と検証**:
   - 入力となるトレースファイル（JSON / JSONL 形式のセッション履歴や tool_uses ログ）の存在とフォーマットを確認する。
2. **再利用可能ステップの抽出**:
   - 統合 CLI `edd harvest-trace` を実行し、トレースからユーザー意図、呼び出されたツール、入出力パラメータを自動抽出してスキル雛形を生成する：
   ```bash
   edd harvest-trace <trace_file.json> <suggested_skill_name> --out src/skills
   ```
3. **静的検証とインバージョン評価の確認**:
   - 自動生成された `SKILL.md` と `tests/<skill>.test.json` に対して静的検証を実行する：
   ```bash
   edd validate src/skills/<suggested_skill_name>
   ```
4. **レビューと後処理**:
   - 抽出された手順のステップ記述（Workflow）が一般的かつ明快であるか確認し、必要に応じて引数の汎用化を行う。

## Examples
- Input: "Harvest a new skill 'data-cleaner' from execution trace ./scratch/data_clean_trace.json" → Output: "Successfully harvested 'data-cleaner' skill with workflow steps and test cases under src/skills/data-cleaner"
- Input: "Turn session log into reusable skill" → Output: "Extracted tool sequence and generated new skill package"

## Output format
- 抽出されたツールシーケンス、生成されたスキルディレクトリのパス、および `edd validate` の検証結果サマリーを提示する。

## Anti-patterns to avoid
- 実行トレースの生ログ（機密トークンや一時パス）をそのままハードコードしてスキル化しないこと。
- 負例（発動してはならない条件）が欠落したドラフトのまま本番昇格させないこと（必ず 3正例＋3負例を整える）。
- 成功実績のないエラーログや中断トレースから無理にスキルを生成しないこと。

## Requirements & Prerequisites
- **Python**: >= 3.11
- **Package**: `pip install -e edd-agent-tools`
- **CLI**: `edd` コマンドが環境パスで解決可能であること
