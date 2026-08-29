---
name: tier3-test-runner
description: "対象スキルに対して軌跡シミュレーションテストおよび敵対的テストを実行し、すべて合格した場合に Tier 3 として登録する評価実行スキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - trajectory-test-executor
  - adversarial-test-executor
---

# Tier 3 Test Runner

## Overview

対象スキルに対して、軌跡シミュレーションテスト（マルチターン・ツール呼び出し検証）および敵対的・レッドチームテスト（プロンプトインジェクション耐性評価）を実行し、最高ランクの防壁を突破したスキルを Tier 3 として登録するワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と各評価セットパスが提供された場合 ➔ **Then** `scripts/runner.py` の `tier3_test_runner` を呼び出し、一連の Tier 3 防壁テストと昇格処理を実行する

## Step-by-Step Instructions

### Step 1: 依存関係の検証 *(Target: `scripts/runner.py`)*

`SkillsState` を通じて対象スキルの依存関係グラフを検証し、DAG構造にエラーがないことを確認する。

### Step 2: 軌跡シミュレーションテストの実行 *(Target: `scripts/runner.py`)*

`SimulationEvalRunner` を用いて、エージェントとのマルチターン対話およびツール呼び出し軌跡（しきい値 90% 以上）を検証する。

### Step 3: 敵対的・レッドチームテストの実行 *(Target: `scripts/runner.py`)*

`SimulationEvalRunner` を用いて、悪意あるプロンプトやシステム境界値に対する堅牢性（しきい値 85% 以上）を検証する。

### Step 4: Tier 3 昇格と登録 *(Target: `scripts/runner.py`)*

すべてのテストが合格した場合にのみ、`SkillsState` において対象スキルのステータスを `SkillTier.TIER3` に更新・永続化する。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルを Tier 3 にオンボーディングしてください。"
- "軌跡テストとレッドチームテストを実行して Tier 3 へ昇格させて。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/runner.py`**: 軌跡テスト、敵対的テスト、Tier 3 登録を一括実行するメインスクリプト

## Guidelines & Best Practices

- いずれかのテストで不合格となった場合は、Tier 3 への昇格を行わずに失敗詳細を返すこと。
- テスト実行環境は隔離された仮想環境（`LocalWorkspaceEnv`）を使用すること。
