---
name: tier2-test-runner
description: "対象スキルに対して契約テスト、ゴールデンテスト、およびジャッジテストを実行し、すべて合格した場合に Tier 2 として登録する評価実行スキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - contract-test-executor
  - golden-test-executor
  - judge-test-executor
---

# Tier 2 Test Runner

## Overview

対象スキルに対して、契約テスト（単体テスト）、ゴールデンテスト（正解例マッチング）、および LLM ジャッジテスト（主観品質評価）を実行し、全テストに合格したスキルをシステムに Tier 2 スキルとして登録するワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と各評価セットパスが提供された場合 ➔ **Then** `scripts/runner.py` の `tier2_test_runner` を呼び出し、一連の Tier 2 防壁テストと昇格処理を実行する

## Step-by-Step Instructions

### Step 1: 依存関係の検証 *(Target: `scripts/runner.py`)*

`SkillsState` を通じて対象スキルの依存関係グラフを検証し、DAG構造にエラーがないことを確認する。

### Step 2: 契約テストの実行 *(Target: `scripts/runner.py`)*

`ContractTestRunner` を用いて、公開関数の契約適合性および境界値動作を検証する。

### Step 3: ゴールデンテストおよびジャッジテストの実行 *(Target: `scripts/runner.py`)*

`SimulationEvalRunner` を用いて、ゴールデン入出力ペア（しきい値 90% 以上）および LLM ジャッジ（しきい値 85% 以上）を実行・評価する。

### Step 4: Tier 2 昇格と登録 *(Target: `scripts/runner.py`)*

すべてのテストが合格した場合にのみ、`SkillsState` において対象スキルのステータスを `SkillTier.TIER2` に更新・永続化する。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルを Tier 2 にオンボーディングしてください。"
- "ゴールデンテストとジャッジテストを実行して Tier 2 へ昇格させて。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/runner.py`**: 契約テスト、ゴールデンテスト、ジャッジテスト、Tier 2 登録を一括実行するメインスクリプト

## Guidelines & Best Practices

- いずれかのテストで不合格となった場合は、Tier 2 への昇格を行わずに失敗詳細を返すこと。
- テスト実行環境は隔離された仮想環境（`LocalWorkspaceEnv`）を使用すること。
