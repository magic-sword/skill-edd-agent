---
name: contract-test-generator
description: "指定されたスキルの SKILL.md 仕様書およびスクリプト実装に基づき、正常系・異常系の入出力契約テストケースを自動生成して保存するスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Contract Test Generator

## Overview

対象スキルの `SKILL.md`（仕様書）および `scripts/` コードを分析し、必須パラメータ検証、型制約、境界値、戻り値スキーマ契約を検証する契約駆動テストケース（`EvalCaseSet`）を自動生成する。

## Workflow Decision Tree

- **If** 対象スキル名と出力先パスが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、契約テストケースを生成して保存する

## Step-by-Step Instructions

### Step 1: 仕様およびコードの分析 *(Target: `scripts/executor.py`)*

対象スキルの `SKILL.md` と `scripts/` 配下の Python スクリプトを読み込み、引数の型・必須属性・戻り値スキーマを抽出する。

### Step 2: 契約テストケースの構造化生成 *(Target: `scripts/executor.py`)*

正常系（最小引数・全引数指定）および異常系（型不一致・必須引数欠落）のテストケースを構造化生成する。

### Step 3: ファイル書き出し *(Target: `scripts/executor.py`)*

生成された評価セットを `EvalCaseSet` 形式で指定された `output_path` に書き出す。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルの契約テストケースを生成してください。"
- "my-skill の unit.evalset.json を作成して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: 契約テスト生成実行エンジン
- **`scripts/eval_case_set_writer.py`**: ファイル出力モジュール

## Guidelines & Best Practices

- 必須引数が欠落した場合に適切な例外（`ValueError` 等）が発生することを検証するケースを含めること。
