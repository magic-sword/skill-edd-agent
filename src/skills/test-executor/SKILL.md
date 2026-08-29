---
name: test-executor
description: "ADK評価シミュレーションを実行し、指定されたスキルの動作検証と合否判定を行う評価実行スキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Test Executor

## Overview

ADK 評価シミュレーション（`LocalWorkspaceEnv`）を実行し、指定されたスキルのテストケース検証、精度計測、および合否判定を行う。

## Workflow Decision Tree

- **If** 対象スキル名と評価セットファイルが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、シミュレーションを実行して結果レポートを出力する

## Step-by-Step Instructions

### Step 1: 環境のセットアップ *(Target: `scripts/executor.py`)*

評価対象スキルのリソースを取得し、テスト用の `LocalWorkspaceEnv` を構築する。

### Step 2: 評価シミュレーションの実行 *(Target: `scripts/executor.py`)*

テストケース（`*.evalset.json`）を順次実行し、エージェントの推論経路およびツール呼び出し結果を計測する。

### Step 3: 結果の判定とレポート保存 *(Target: `scripts/executor.py`)*

計測された精度と閾値を比較して合否を判定し、`tests/results/latest_report.json` に詳細ログを保存する。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルのテストシミュレーションを実行して結果を教えて。"
- "unit.evalset.json を使って my-skill の動作を検証してください。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: ADK シミュレーション実行エンジン
- **`scripts/handler.py`**: エントリポイントハンドラ

### `assets/` (Output Templates & Boilerplates)
- **`assets/default_eval_config.json`**: デフォルト評価設定ファイル

## Guidelines & Best Practices

- 実行前にテストケースファイル（`*.evalset.json`）が有効な JSON 形式であることを確認すること。

