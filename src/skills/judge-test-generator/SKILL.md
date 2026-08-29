---
name: judge-test-generator
description: "対象スキルの SKILL.md およびスクリプト仕様から評価ルーブリック基準と検証用引数のペアを自動設計し、[skill_name]_judge.evalset.jsonとして書き出すスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Judge Test Generator

## Overview

対象スキルの `SKILL.md`（仕様書）および実装スクリプトから、複数の詳細な評価ルーブリック基準（criterion, description, weight）と検証用引数（inputs）のペアを自動設計し、`[skill_name]_judge.evalset.json` として書き出すスキル。

## Workflow Decision Tree

- **If** 対象スキル名と出力先パスが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、ジャッジテストケースを生成してファイルへ出力する

## Step-by-Step Instructions

### Step 1: 仕様のロードと解析 *(Target: `scripts/executor.py`)*

対象スキルの `SKILL.md` および `scripts/` リソースを `SkillsState` 経由で取得し、評価すべき品質基準とパラメータ仕様を解析する。

### Step 2: ジャッジケースとルーブリックの生成 *(Target: `scripts/executor.py`)*

多角的な品質観点（正確性、完全性、文体、制約遵守等）に基づく重み付きルーブリック項目を含むテストケースセットを構造化生成する。

### Step 3: ファイル書き出し *(Target: `scripts/executor.py`)*

生成された評価セットを JSON 形式で指定された `output_path` に書き出す。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルのジャッジ評価テストケースを作成してください。"
- "my-skill のルーブリック評価セットを生成して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: ジャッジテスト生成の実行エンジン
- **`scripts/prompter.py`**: プロンプト構築モジュール
- **`scripts/handler.py`**: エントリポイントハンドラ

### `assets/` (Output Templates & Boilerplates)
- **`assets/prompts/generate_judge_cases.txt`**: LLM生成プロンプトテンプレート

## Guidelines & Best Practices

- ルーブリック基準は客観的かつ判定可能な形式で記述すること。
- 生成されたテストケースは `judge-test-executor` で評価実行できること。

