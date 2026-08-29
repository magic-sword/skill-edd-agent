---
name: adversarial-test-generator
description: "対象スキルの SKILL.md 仕様書および scripts/ 配下のコードを分析し、敵対的プロンプトや限界値・異常値を含むセキュリティ＆頑健性テストケースセットを自動生成するスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Adversarial Test Generator

## Overview

対象スキルの `SKILL.md`（仕様書）および `scripts/` コードを分析し、プロンプトインジェクション、境界値、型制約違反、例外系シナリオを検証する敵対的（Adversarial）評価テストケース（`EvalCaseSet`）を自動生成する。

## Workflow Decision Tree

- **If** 対象スキル名と出力先パスが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、敵対的テストケースを生成して保存する

## Step-by-Step Instructions

### Step 1: 仕様およびコードの分析 *(Target: `scripts/executor.py`)*

対象スキルの `SKILL.md` と `scripts/` 配下の Python スクリプトを読み込み、入力制約、エラーハンドリング、脆弱になりうるポイントを特定する。

### Step 2: 敵対的・限界テストケースの構造化生成 *(Target: `scripts/executor.py`)*

インジェクション攻撃、極端な境界値、型違反などの異常系テストケースを構造化生成する。

### Step 3: ファイル書き出し *(Target: `scripts/executor.py`)*

生成された評価セットを `EvalCaseSet` 形式で指定された `output_path` に書き出す。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルの敵対的テストケースを生成してください。"
- "my-skill のセキュリティ・限界評価テストケースを作って。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: 敵対的テスト生成実行エンジン
- **`scripts/prompter.py`**: プロンプト構築モジュール

## Guidelines & Best Practices

- 単なるランダムなエラー入力だけでなく、エージェントの安全ガードレールを回避しようとするプロンプトインジェクションを含めること。
