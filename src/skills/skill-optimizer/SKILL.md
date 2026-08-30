---
name: skill-optimizer
description: This skill should be used when managing the autonomous self-healing and improvement loop, verifying patches, running cascade regression tests, and promoting skills to Tier 1-3.
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - skill-diagnoser
  - skill-evaluator
---

# Skill Optimizer

## Overview

エージェント自身が主体となり、テスト失敗を起点とした診断（`skill-diagnoser`）、コードや仕様書の安全な修正、静的バリデーション、再テスト、および依存する上位ワークフローに対する連鎖回帰テスト（Cascade Testing）を経て、安全に Tier 昇格させる自律改善ループ（Self-Improvement Loop）のオーケストレーション・ワークフロー。

## Workflow Decision Tree

- **If** スキルに不具合やテスト失敗がある場合 ➔ **Then** Step 1 で診断コンテキストを取得し、Step 2 でエージェント自らコード/仕様を修正後、`scripts/optimizer.py` で検証・連鎖回帰テスト・昇格を実行する
- **If** すでに全テストに合格しているスキルの昇格を行う場合 ➔ **Then** `scripts/optimizer.py <skill_name> --target-tier 1` を直接実行する

## Step-by-Step Instructions

### Step 1: テスト実行と失敗診断 *(Tool: `skill-diagnoser`)*

1. `skill-evaluator` または `scripts/optimizer.py` を呼び出してテストを実行する。
2. 失敗が検知された場合、依存スキル `skill-diagnoser` を実行して失敗コンテキスト（エラー、スタックトレース、該当ソースコード）を取得する。

### Step 2: エージェントによる原因推論とファイル修正

取得したコンテキストに基づき、エージェント自身が原因を分析し、ファイル編集ツール（`replace_file_content` や `SafeEditFileTool`）を用いて対象ファイルを修正する：
- ロジック修正: `src/skills/<skill_name>/scripts/*.py`
- 仕様・トリガー修正: `src/skills/<skill_name>/SKILL.md`
- テストケース修正: `src/skills/<skill_name>/tests/*.evalset.json`

### Step 3: 静的検証・連鎖回帰テスト・Tier 昇格 *(Tool: `scripts/optimizer.py`)*

修正適用後、決定論的検証ツールを実行して単体検証・連鎖回帰テスト・Tier 昇格を一括実行する：
```bash
python scripts/optimizer.py <skill_name> --target-tier 1 --cascade
```
- すべてのテストに合格した場合、スキルは自動的に `SkillsState` 上で昇格登録される。
- 再度失敗した場合は、Step 1 に戻り最大 3 回まで修復ループを反復する。

## Usage Scenarios & Trigger Examples

- "失敗した case-converter スキルを自律修復して Tier 1 に昇格させてください。"
- "作成したスキルの検証と上位連鎖回帰テストを実行して昇格させて。"

## When NOT to Use This Skill

- **新規要件から一からスキルを設計・作成する場合**: 修復ループではなく、`skill-creator` を使用する。
- **スキルの評価やスコア測定のみを単発で実行する場合**: 最適化ループではなく、`skill-evaluator` を使用する。
- **失敗原因の診断レポートのみを閲覧したい場合**: `skill-diagnoser` を使用する。

## Bundled Resources

### `scripts/` (Executable Tools - Zero-LLM)
- **`scripts/optimizer.py`**: 静的検証・単体テスト・連鎖回帰テスト・Tier昇格登録を決定論的に実行する CLI ツール

## Guidelines & Best Practices

- 修正適用後は必ず `SkillValidator` および連鎖回帰テストを通過させること。
- 無限ループを防ぐため、最大リトライ回数（デフォルト 3回）を設定すること。
