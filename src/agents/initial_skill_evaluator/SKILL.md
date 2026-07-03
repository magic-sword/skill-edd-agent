---
name: initial_skill_evaluator
description: 新規スキルを評価し、その結果に基づいてスキルティアを登録・昇格させるワークフロー。
dependencies:
  - skill-manager
  - trigger-evaluator
  - test-executor
  - eval-unit-tester
---

# initial_skill_evaluator

## 概要

生成されたスキルを一番最初に評価するワークフロー。以下のステップを実行します：
1. set_skill_tier (command='register') を呼び出して、スキルが未登録であれば Tier 0 で登録する。
2. generate_trigger_tests を呼び出して、対象スキルのトリガーチェックのテストケースを生成する。
3. run_skill_tests (eval_mode=0, threshold_accuracy=0.90) を呼び出して、生成したトリガーテストケースを実行する.
4. generate_unit_tests を呼び出して、対象スキルのユニットテストのテストケースを生成する。
5. run_skill_tests (eval_mode=1, threshold_accuracy=1.0) を呼び出して、生成したユニットテストケースを実行する。
6. set_skill_tier (command='set-tier', tier=1) を呼び出して、対象スキルが Tier 0 であれば Tier 1 へ昇格させる。

## 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill_name | str | はい | 評価対象スキルの名前 |
| skill_id | str | はい | 評価対象スキルのID |

## 実行方法

```bash
python3 src/agents/initial_skill_evaluator/scripts/main.py \
  --skill_name <スキル名> \
  --skill_id <スキルID>
```

## 依存関係

このワークフローサブエージェントは以下のスキルに依存しています。

*   **skill-manager**:
    *   スキルの登録、ティアの設定、および状態管理を行います。
    *   `set_skill_tier`関数を使用し、スキルをTier 0で登録したり、テスト結果に基づいてTier 1に昇格させたりします。

*   **trigger-evaluator**:
    *   指定されたスキルのトリガーテストケースを生成します。
    *   `generate_trigger_tests`関数を使用し、スキルのトリガー条件が正しく機能するかを評価するためのテストデータを準備します。

*   **test-executor**:
    *   生成されたテストケース（トリガーテスト、ユニットテスト）を実行し、その結果を評価します。
    *   `run_skill_tests`関数を使用し、テスト結果の精度を検証します。

*   **eval-unit-tester**:
    *   指定されたスキルのユニットテストケースを生成します。
    *   `generate_unit_tests`関数を使用し、スキルの内部ロジックや特定の機能が期待通りに動作するかを評価するためのテストデータを準備します。
