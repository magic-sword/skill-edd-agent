---
name: skill-optimizer
description: This skill should be used when automatically repairing failing skills, applying patches across skill resources, and executing regression cascade tests for tier promotion.
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - skill-diagnoser
  - skill-evaluator
---

# Skill Optimizer

## Overview

テスト失敗ログや評価レポートを起点とし、`skill-diagnoser` による根本原因分析・改善計画（`ImprovementPlan`）の策定、コードおよび `SKILL.md` への安全な自動パッチ適用、静的リンター検証、再テスト、そして依存する上位ワークフローに対する連鎖回帰テスト（Cascade Testing）までを完全自動でループ実行する自律改善エンジン。

## Workflow Decision Tree

- **If** テストが失敗しているスキルが指定された場合 ➔ **Then** `scripts/optimizer.py` を呼び出し、自律修復ループを実行して Tier 昇格させる
- **If** すでに全テストに合格している場合 ➔ **Then** 連鎖回帰テストのみを確認して即座に完了する

## Step-by-Step Instructions

### Step 1: テスト実行と結果判定 *(Target: `scripts/optimizer.py`)*

対象スキルのテストを実行し、合格・不合格およびスコアを測定する。

### Step 2: 診断と改善計画の取得 *(Target: `scripts/optimizer.py`)*

不合格の場合、`skill-diagnoser` を呼び出して `ImprovementPlan`（修正レイヤー、原因、具体的パッチ指示）を取得する。

### Step 3: 安全なパッチ適用と静的検証 *(Target: `scripts/optimizer.py`)*

計画に基づき、`SKILL.md` または `scripts/*.py` へ差分を適用し、`SkillValidator` による静的整合性を検証する。

### Step 4: 再テストと連鎖回帰テスト *(Target: `scripts/optimizer.py`)*

再テストを実行して合格を確認後、`CascadeTestRunner` により依存する上位ワークフローの回帰テストを一括実行し、Tier 1 へ昇格登録する。

## Usage Scenarios & Trigger Examples

- "失敗した my-skill を自律修復して Tier 1 に昇格させてください。"
- "最新のテストレポートを元にスキルを自動改善（最適化）して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/optimizer.py`**: 自律改善ループ実行エンジン
- **`scripts/main.py`**: エントリポイントモジュール

## Guidelines & Best Practices

- 修正適用後は必ず `SkillValidator` を実行し、構文エラーやファイル参照切れが発生していないことを確認すること。
- 無限ループを防ぐため、最大リトライ回数（デフォルト 3回）を設定すること。
