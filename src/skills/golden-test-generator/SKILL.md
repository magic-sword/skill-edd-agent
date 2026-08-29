---
name: golden-test-generator
description: "対象スキルの SKILL.md およびスクリプト仕様を分析し、意味的ゴールデンアウトプット評価用のテストケースセットを自動生成して書き出すスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Golden Test Generator

## Overview

対象スキルの `SKILL.md`（仕様書）および実装スクリプトを分析し、多様なユースケース入力値と、期待される正解（意味的ゴールデンアウトプット）のペアをLLMで自動生成し、`[skill_name]_golden.evalset.json` として書き出すワークフロー。

## Workflow Decision Tree

- **If** 対象スキル名と出力先パスが指定された場合 ➔ **Then** `scripts/executor.py` を呼び出し、ゴールデンテストケースを生成してファイルへ出力する

## Step-by-Step Instructions

### Step 1: 仕様のロードと解析 *(Target: `scripts/executor.py`)*

対象スキルの `SKILL.md` および `scripts/` リソースを `SkillsState` 経由で取得し、入力パラメータと期待される挙動を解析する。

### Step 2: ゴールデンケースの生成 *(Target: `scripts/executor.py`)*

正常系、境界値・エッジケース、例外系を含むテスト入力値と期待される出力ルーブリックを構造化生成する。

### Step 3: ファイル書き出し *(Target: `scripts/executor.py`)*

生成された評価セットを JSON 形式で指定された `output_path` に書き出す。

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルのゴールデンテストケースを生成してください。"
- "my-skill の仕様書から golden.evalset.json を作成して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: ゴールデンテスト生成の実行エンジン
- **`scripts/prompter.py`**: プロンプト構築モジュール
- **`scripts/handler.py`**: エントリポイントハンドラ

### `assets/` (Output Templates & Boilerplates)
- **`assets/prompts/generate_golden_cases.txt`**: LLM生成プロンプトテンプレート

## Guidelines & Best Practices

- 必ず対象スキルの `SKILL.md` が最新の状態であることを確認してから実行すること。
- 生成されたテストケースは `golden-test-executor` で検証可能であること。

