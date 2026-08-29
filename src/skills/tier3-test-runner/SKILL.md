---
name: tier3-test-runner
description: "指定されたスキルに対して軌跡（Trajectory）テストおよび敵対的（Adversarial）テストを実行し、自律適応力と安全性を総合評価してTier 3に登録するワークフロー。"
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - adversarial-test-executor
  - golden-test-executor
  - judge-test-executor
---

# Tier 3 Test Runner

## Overview

指定されたスキルに対して、複雑なタスク解決経路を評価する軌跡（Trajectory）テストおよび敵対的入力・異常系に対する頑健性を評価するアドバーサリアル（Adversarial）テストを実行し、すべてのテストに合格した場合にスキルを Tier 3 としてシステムに登録するワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と評価セットパスが指定された場合 ➔ **Then** `scripts/handler.py` を呼び出し、Tier 3 評価パイプラインを実行する

## Step-by-Step Instructions

### Step 1: 依存関係検証 *(Target: `scripts/nodes/validate_dependencies.py`)*

評価対象スキルの前提リソースおよび依存スキルが利用可能であることを確認する。

### Step 2: ゴールデン・ジャッジテスト実行 *(Target: `scripts/nodes/run_golden_test.py`)*

ゴールデンテストおよびルーブリックジャッジテストを実行し、高精度な意味的整合性を評価する。

### Step 3: アドバーサリアルテスト実行 *(Target: `scripts/nodes/run_adversarial_test.py`)*

`adversarial-test-executor` を呼び出し、悪意のある入力や境界値に対する安全性を評価する。

### Step 4: Tier 3 登録 *(Target: `scripts/nodes/register_tier3.py`)*

すべてのテストに合格した場合、対象スキルをシステムに Tier 3 として登録する。

## Usage Scenarios & Trigger Examples

- "my-skill に対して Tier 3 昇格テストを実行してください。"
- "軌跡テストとアドバーサリアルテストで my-skill の頑健性を評価して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/handler.py`**: ワークフロー実行エントリポイント
- **`scripts/nodes/`**: 各実行ステップノード

## Guidelines & Best Practices

- Tier 3 テストは高難度のシナリオを含むため、Tier 2 合格済みのスキルに対して実行すること。
