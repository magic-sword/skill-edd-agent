---
name: generate-skill-workflow
description: 新規スキルを自動生成し、単体テスト・トリガーテストに合格させて Tier 1 に正式本登録する上位ワークフロー。
dependencies:
  - skill-manager
  - skill-generator
  - eval-unit-tester
  - test-executor
  - trigger-evaluator
---

# generate-skill-workflow

## 概要

ユーザーから提供されたスキル名と要件プロンプトをもとに、以下の 7 ステップを決定論的に順次実行し、
品質保証済みのスキルを自動的に正式登録するワークフローです。

1. スキルの仮登録（Tier 0）
2. スキル本体コードの自動生成
3. 単体テストケースの自動生成
4. 単体テストの実行と合格確認（精度 100%）
5. トリガーテストケースの自動生成
6. トリガーテストの実行と合格確認（精度 90%）
7. スキルの正式本登録（Tier 1）とクリーンアップ

## 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill_name | string | ✅ | 作成するスキルの名前（ケバブケース） |
| prompt | string | ✅ | スキルの仕様・要件プロンプト |

## 実行方法

```bash
PYTHONPATH=src python3 src/workflows/run_workflow.py \
  --workflow_name generate-skill-workflow \
  --skill_name <スキル名> \
  --prompt "<要件プロンプト>"
```

## 依存関係

このワークフローは以下の単体スキルに依存しています。
依存するスキルが `skills_registry.json` に登録されていない場合、実行は事前に拒否されます。

- **skill-manager**: スキルの Tier 登録・管理
- **skill-generator**: ADK サブエージェントによるスキル本体コード生成
- **eval-unit-tester**: 単体テストケースの自動生成
- **test-executor**: テストの実行と精度判定
- **trigger-evaluator**: トリガー精度テストケースの自動生成
