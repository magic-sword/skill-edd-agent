---
name: adk-optimizer
description: |
  Runs an autonomous refactoring loop using ephemeral Antigravity CLI (agy) sessions to optimize the codebase according to Google ADK 2.0 best practices.
  Use when you want to eliminate reinvented wheels, remove obsolete legacy architectures, and align with ADK 2.0 without context degradation.
  Do NOT use for single-line ad-hoc tweaks or running standard application code.
license: MIT
allowed-tools: run_command view_file
metadata:
  pattern: workflow
---

# ADK 2.0 Optimizer (Autonomous Refactoring Loop)

## When to use
- Google ADK 2.0 公式ベストプラクティスに従い、プロジェクト全体を自動で監査・リファクタリングしたい時
- プロジェクト内に残存する車輪の再発明（自前 subprocess、不要ラッパー、独自Judge）や旧設計思想を排除したい時
- コンテキストウィンドウの劣化（Context Rot）を起こさず、クリーンなセッション（Ephemeral Sessions）で改善を反復したい時
- 夜間やバックグラウンドで自律的にテスト・修正・コミットを回したい時

## When NOT to use
- 単発の 1 行修正や通常のコーディング対話
- 単純な `pytest` の手動実行
- 新規スキルの雛形作成（`skill-creator` を使用すること）

## Workflow
1. **未コミット変更の整理**:
   - 作業ツリーに未コミットの変更がないか確認する。
   ```bash
   git status -s
   ```
2. **自律ループの起動**:
   - `scripts/run_adk_loop.py` を実行する。
   ```bash
   # デフォルト (最大 10 反復)
   python3 .agents/skills/adk-optimizer/scripts/run_adk_loop.py

   # 反復回数を指定して実行
   python3 .agents/skills/adk-optimizer/scripts/run_adk_loop.py --max-iterations 5

   # Dry-run による事前構成検証
   python3 .agents/skills/adk-optimizer/scripts/run_adk_loop.py --dry-run
   ```
3. **ループの進行プロセスの監視**:
   - 各反復で独立した `agy` プロセスが起動し、以下を自律実行する：
     - MCP `google-developer-knowledge` による ADK 2.0 最新仕様の確認
     - チェックリストに基づく監査と 1 箇所のピンポイント改修
     - `pytest` による自動回帰テスト
     - テスト合格時の `git commit`
     - 改善点解消時の `OPTIMIZATION_COMPLETE` シグナル出力
   - ログは `.adk_optimization_loop.log` にリアルタイム記録される。

## Examples
- Input: "プロジェクト全体を ADK 2.0 ベストプラクティスに自律ループで最適化して"
  Output: "ADK 2.0 自律最適化ループを開始しました。進捗ログ: .adk_optimization_loop.log"
- Input: "run_adk_loop.py を dry-run で確認して"
  Output: "プロンプトテンプレートおよびコマンド構成の検証が完了しました（正常）"

## Output format
- 反復ごとのコミットハッシュ、テスト成否、および最終的な収束結果（完了 / 最大反復到達）を表示する。

## Anti-patterns to avoid
- 大量の変更を 1 セッションで一気に行おうとしない（1 反復 1 コミットの原則を遵守すること）。
- テストが壊れた状態のままコミットを継続しない（スクリプトの自動ロールバック保護を活用すること）。
- MCP 照合をスキップして推測で ADK 2.0 仕様を改修しない。

## Requirements & Prerequisites
- **Antigravity CLI (`agy`)**: バージョン 1.1.1 以上（`agy --version`）
- **MCP サーバー**: `google-developer-knowledge` が `~/.gemini/antigravity-cli/mcp` に配備されていること
- **Python**: >= 3.10
- **Git**: リポジトリが初期化され、クリーンな作業状態であること

## Bundled Resources
### `references/`
- **`references/checklist.md`**: Google ADK 2.0 準拠性チェックリスト（監査項目）
- **`references/prompt_template.md`**: 各セッションに渡す高精度プロンプトの SSOT
### `scripts/`
- **`scripts/run_adk_loop.py`**: 自律ループの親コントローラー
