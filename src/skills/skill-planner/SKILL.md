---
name: skill-planner
description: "要件プロンプトを分析し、最適な開発ルート（新規作成、既存更新、事前提案）と推奨構成を特定して計画立案するスキル。"
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Planner

## Overview

ユーザーの要件プロンプトを分析し、既存のスキル資産を照合した上で、新規スキルの作成、既存スキルの改修、または複合ワークフローの構築計画を立案する。

## Workflow Decision Tree

- **If** 要件プロンプトが提供された場合 ➔ **Then** `scripts/executor.py` を呼び出し、最適な開発ルートと構成計画を策定する

## Step-by-Step Instructions

### Step 1: 既存スキル資産の収集 *(Target: `scripts/executor.py`)*

`SkillsState` を通じて登録されている既存スキルの一覧とメタデータをロードする。

### Step 2: 要件の分析とルート判定 *(Target: `scripts/executor.py`)*

ユーザー要件と既存スキルを照合し、`create_skill`, `update_skill`, `create_workflow`, `update_workflow`, `proposal` のいずれかのルートを判定する。

### Step 3: 計画の構造化出力 *(Target: `scripts/executor.py`)*

分析根拠、対象スキル、依存関係、および事前開発提案を含む計画オブジェクトを出力する。

## Usage Scenarios & Trigger Examples

- "新しいスキル開発の計画を立ててください。"
- "PDF結合機能を既存スキルに追加したいので分析して。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/executor.py`**: 計画立案の実行エンジン
- **`scripts/prompter.py`**: プロンプト構築モジュール
- **`scripts/handler.py`**: エントリポイントハンドラ

## Guidelines & Best Practices

- 既存スキルの重複作成を避け、可能な限り既存アセットの再利用・拡張を提案すること。

