---
name: library-evolver
description: |
  Autonomously expands and evolves the agent's skill library when facing capability gaps or novel tasks.
  Use when encountering unsupported tasks, synthesizing new skills from requirements, or coordinating full self-evolution lifecycles.
  Do NOT use for manual single-line edits or direct business data processing.
license: MIT
allowed-tools: run_skill_script load_skill_resource
metadata:
  pattern: workflow
---

# Library Evolver

## When to use
- エージェントが未対応のタスク要求や未実装ツールに遭遇し、自律的にスキルライブラリを拡張したい時
- ユーザーからの「この機能を追加して」「自律的に進化させて」という要求に応じ、新規スキルの開発〜登録を一括実行したい時
- スキル候補のセマンティック衝突（重複）を検証し、新規作成か既存改修かを自動判定したい時
- 昇格済みの新規スキルを即座にエージェントカタログ（A2A v1.0.0 `agent-card.json`）へ反映したい時

## When NOT to use
- 単発のスクリプト実行や手動の一行修正（直接編集または専用ツールを使用すること）
- 既存スキルの単体リファクタリングやバグ修正のみが目的の時（`skill-evolver` を使用すること）
- 単純な静的構文チェックのみの時（`edd validate` を使用すること）

## Workflow
1. **Gap Analysis & Collision Check**:
   - スクリプト `scripts/library_evolver.py` を呼び出し、タスク要求に対する新規スキル候補を起票：
     ```bash
     python3 src/skills/library-evolver/scripts/library_evolver.py --action plan --task "<task_description>" --skill-name <suggested-name>
     ```
   - 既存スキルとの意味的衝突（Clarity Check）を評価し、`SYNTHESIZE_NEW` または `EVOLVE_EXISTING` の方針を確定する。
2. **Deterministic Scaffolding (EDD Inversion)**:
   - `edd init <skill-name>` を実行し、3正例＋3負例のテストケース先行でパッケージ雛形を初期化する。
3. **Skill Implementation**:
   - 白書 Appendix A 準拠の minimal 6大必須セクションを持つ `SKILL.md`、および `scripts/`、`references/` を実装する。
4. **Verification & Tier Promotion**:
   - `edd validate src/skills/<skill-name>` で静的整合性を確認。
   - `edd optimize <skill-name> --tier 1` を実行し、契約テスト・Co-loading・Red-teaming を通過させて Tier 昇格。
5. **Catalog & Card Synchronization**:
   - `scripts/library_evolver.py` を `--action register` で呼び出すか、`edd sync-card` を実行して `src/agent-card.json` に新スキルを反映する。

## Examples
- Input: "自律的に未対応の画像圧縮スキル image-compressor を開発してカタログに追加して"
  Output: Gap分析完了 ➔ 衝突なし確認 ➔ 雛形生成 ➔ 6大セクション実装 ➔ 評価ゲート通過 ➔ Tier 1 昇格 ➔ Agent Card 自動反映。

## Output format
- 進化実行サマリー（起票スキル名、衝突検知結果、通過テスト、昇格Tier、更新された Agent Card 情報）を客観的 Markdown で出力する。

## Anti-patterns to avoid
- 既存スキルと類似した機能を重複して乱立させない（必ず `edd check-collision` を通す）。
- テストケース（3正例＋3負例）を作成する前に `SKILL.md` を書き始めない（EDD Inversion を徹底する）。
- 大文字の命令文（`ALWAYS`, `NEVER`）をプロンプトに累積させない（Rationale を説明する）。

## Requirements & Prerequisites
- Python: >= 3.10
- Package: edd-agent-tools

## Bundled Resources
### `scripts/`
- `scripts/library_evolver.py`: 自律ライブラリ進化オーケストレーションスクリプト。

### `references/`
- `references/evolution_lifecycle.md`: Voyager型自己増殖ライフサイクルの詳細仕様書。
