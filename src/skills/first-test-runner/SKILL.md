---
name: first-test-runner
description: "対象スキルの依存関係、トリガーテスト、および契約テストを実行し、すべて合格した場合に Tier 1 として登録する評価実行スキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - trigger-test-executor
  - test-executor
---

# First Test Runner

## Overview

対象スキルの依存関係（DAG整合性）、トリガーテスト（インテント分類）、および契約テスト（単体テスト）を実行し、全テストに合格したスキルをシステムに Tier 1 スキルとして登録するワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と評価セットパスが提供された場合 ➔ **Then** `scripts/runner.py` の `tier1_skill_onboarding` を呼び出し、一連の防壁テストと Tier 1 昇格を実行する

## Step-by-Step Instructions

### Step 1: 依存関係の検証 *(Target: `scripts/runner.py`)*

`SkillsState` を通じて対象スキルの依存関係グラフを検証し、循環依存や未解決の依存スキルが存在しないことを確認する。

### Step 2: 契約テストの実行 *(Target: `scripts/runner.py`)*

`ContractTestRunner` を用いて、対象スキルの公開関数に対する入力バリデーション、戻り値型検証、境界値アサーションを実行する。

### Step 3: トリガーテストの実行 *(Target: `scripts/runner.py`)*

`SimulationEvalRunner` を用いて、対象スキルのトリガー発話に対するインテント分類精度（しきい値 90% 以上）を検証する。

### Step 4: Tier 1 昇格と登録 *(Target: `scripts/runner.py`)*

すべての検証が合格した場合にのみ、`SkillsState` において対象スキルのステータスを `SkillTier.TIER1` に更新・永続化する。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルを Tier 1 にオンボーディングしてください。"
- "新しいスキルの登録テストを実行し、Tier 1 へ昇格させて。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/runner.py`**: 依存関係検証、契約テスト、トリガーテスト、Tier 1 登録を一括実行するメインスクリプト

## Guidelines & Best Practices

- いずれかのテストで不合格または警告が出た場合は、Tier 1 への昇格を行わずに即座に失敗理由を返すこと。
- テスト実行環境は隔離された仮想環境（`LocalWorkspaceEnv`）を使用すること。
