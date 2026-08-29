---
name: trigger-test-generator
description: "対象スキルの SKILL.md 仕様を分析し、インテント判定評価用（正例・負例プロンプト）のテストケースセットを自動生成して書き出すスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Trigger Test Generator

## Overview

対象スキルの `SKILL.md`（仕様書）を分析し、仕様の明確性チェックを行った上で、エージェントのトリガー精度評価用テストケース（正例・負例プロンプト集）を自動生成し、`[skill_name]_trigger.evalset.json` として書き出すワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と出力先パスが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、トリガー評価テストケースを生成してファイルへ出力する

## Step-by-Step Instructions

### Step 1: 仕様のロードと明確性検証 *(Target: `scripts/executor.py`)*

対象スキルの `SKILL.md` をロードし、トリガー条件や説明文が十分に明確かつ具体的であるかを検証する。

### Step 2: 正例・負例プロンプトの生成 *(Target: `scripts/executor.py`)*

対象スキルが起動すべきプロンプト（Positive cases）と、類似しているが起動すべきでないプロンプト（Negative cases）のペアを構造化生成する。

### Step 3: ファイル書き出し *(Target: `scripts/executor.py`)*

生成された評価セットを `TrajectoryEvalSet` 準拠の JSON 形式で指定された `output_path` に書き出す。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルのトリガーテストケースを生成してください。"
- "my-skill の仕様書から trigger.evalset.json を作成して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: トリガーテスト生成の実行エンジン
- **`scripts/skill_spec_loader.py`**: SKILL.md 仕様ロードモジュール
- **`scripts/llm_evaluator.py`**: 仕様評価およびプロンプト生成モジュール
- **`scripts/test_case_writer.py`**: テストケースファイル出力モジュール

## Guidelines & Best Practices

- 負例プロンプト（Negative cases）は、他のスキルとの境界を正確にテストできるように難易度の高いケースを含めること。
- 生成されたテストセットは `trigger-test-executor` で評価実行できること。

