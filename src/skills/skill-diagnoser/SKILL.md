---
name: skill-diagnoser
description: "テスト失敗結果ログおよび SKILL.md、scripts/ 配下のコードを多角的に分析し、根本原因の特定と構造化された改善計画（ImprovementPlan）を自動策定する診断スキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Diagnoser

## Overview

テストランナーが生成した `tests/results/latest_report.json`、仕様書（`SKILL.md`）、および `scripts/` 配下の Python コードを多角的に分析し、最小限の安全な修正でテストを合格させるための根本原因と `ImprovementPlan` を策定するワークフロー。

## Workflow Decision Tree

- **If** テスト結果レポートが存在し失敗ケースがある場合 ➔ **Then** `scripts/diagnoser.py` を呼び出し、原因を分析して `ImprovementPlan` を出力する
- **If** すべてのテストが合格している場合 ➔ **Then** `verdict="no_issues_found"` として追加改善をスキップする

## Step-by-Step Instructions

### Step 1: テスト結果とスキルのロード *(Target: `scripts/diagnoser.py`)*

失敗したテストレポート（`latest_report.json`）と、対象スキルの `SKILL.md` および `scripts/` コードを読み込む。

### Step 2: 失敗原因の分析とレイヤー特定 *(Target: `scripts/diagnoser.py`)*

エラーメッセージ、スタックトレース、失敗ケースの入出力を精査し、修正すべきレイヤー（`spec`, `script`, `reference`, `asset`, `test_case`）と原因カテゴリを特定する。

### Step 3: 改善計画（ImprovementPlan）の策定 *(Target: `scripts/diagnoser.py`)*

具体的な修正指示（コード差分、説明文更新、テスト期待値修正）を含む `ImprovementPlan` を構造化出力する。

## Usage Scenarios & Trigger Examples

このスキルは以下のようなリクエストでトリガーされる：

- "pdf-tools スキルのテスト失敗原因を診断してください。"
- "最新のテストレポートから改善計画を策定して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/diagnoser.py`**: テスト結果とアセットを分析し改善計画を策定する診断エンジン（CLI対応）
- **`scripts/main.py`**: CLIおよびエージェント向け公開関数（`diagnose_skill_failure`）のエントリポイント

## Guidelines & Best Practices

- 原因の特定は、テスト期待値の誤りなのか、実装コードのバグなのか、SKILL.mdの説明不足なのかを厳密に区別すること。
- 必要最小限かつ安全な修正計画を提示すること。
- スクリプトは `--help` でオプションを確認した上で直接コマンドラインから実行すること。

