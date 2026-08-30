---
name: skill-evaluator
description: This skill should be used when generating multi-layer evaluation test sets, running test suites, or gating skill tier promotions (Tier 1-3) based on Evaluation-Driven Development.
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Evaluator

## Overview

対象スキルの多層評価テストセット（Trigger, Contract, Golden, Judge, Trajectory, Adversarial）の自律生成、サンドボックス環境でのシミュレーション実行、および Tier 1（Production）、Tier 2（Verified）、Tier 3（Mastered）への昇格判定を一括して実行する統合評価エンジン。

## Workflow Decision Tree

評価目的に応じて、以下の決定ロジックに従って評価パイプラインを実行する：

- **If** テストケース（evalset.json）を新規生成する場合 ➔ **Then** `scripts/generate_evalset.py` を呼び出し、対象テストタイプ（`trigger`, `contract`, `golden`, `judge`, `trajectory`, `adversarial`, または `all`）の評価セットを出力する
- **If** 既存の評価セットを実行してスコアを計測する場合 ➔ **Then** `scripts/run_eval.py` を呼び出し、結果を `tests/results/latest_report.json` に構造化ログとして永続化する
- **If** 対象スキルを特定 Tier に昇格・オンボーディング判定する場合 ➔ **Then** `scripts/run_tier_gate.py` を呼び出し、Tier 1〜3 の防壁テストを実行して合格時に `SkillsState` へ登録する

## Step-by-Step Instructions

### Step 1: テストセットの生成 *(Target: `scripts/generate_evalset.py`)*

対象スキルの `SKILL.md` および `scripts/` を解析し、指定された評価タイプのテストセット（`EvalCaseSet` または `TrajectoryEvalSet`）を生成して `tests/<skill_name>_<type>.evalset.json` に保存する。

### Step 2: 評価シミュレーションの実行 *(Target: `scripts/run_eval.py`)*

隔離環境（`LocalWorkspaceEnv`）上でテストを実行し、精度（Accuracy）、成功数、失敗ログを収集して `latest_report.json` に記録する。

### Step 3: Tier 昇格ゲートキーパー判定 *(Target: `scripts/run_tier_gate.py`)*

Tier 階層に応じた防壁テストを実行する：
- **Tier 1 (Production)**: 依存関係グラフ検証 (DAG) + 契約テスト (100%合格) + トリガーテスト (精度 90%以上)
- **Tier 2 (Verified)**: Tier 1 要件 + ゴールデンテスト (精度 90%以上) + LLMルーブリックジャッジテスト (精度 85%以上)
- **Tier 3 (Mastered)**: Tier 2 要件 + 推論軌跡テスト (ToolUse一致) + 敵対的堅牢性テスト (精度 90%以上)

## Usage Scenarios & Trigger Examples

このスキルは以下のようなリクエストでトリガーされる：

- "pdf-tools スキルの契約テストとトリガーテストを生成してください。"
- "新しいスキル text-analyzer の Tier 1 オンボーディングテストを実行して昇格させて。"
- "data-visualizer スキルのゴールデンテストを実行してスコアレポートを出力してください。"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/generate_evalset.py`**: テストケース自動生成スクリプト（CLI / API）
- **`scripts/run_eval.py`**: 評価スイート実行＆ログ永続化スクリプト（CLI / API）
- **`scripts/run_tier_gate.py`**: Tier 1〜3 昇格判定＆登録ゲートキーパー（CLI / API）

### `references/` (On-Demand Knowledge)
- **`references/evaluation_rubrics.md`**: 各テストタイプの合格基準、閾値、および採点ルーブリック仕様書
- **`references/test_types_guide.md`**: 6大テストタイプの設計原則と活用ガイド

### `assets/` (Output Templates & Boilerplates)
- **`assets/sample_evalset.json`**: 評価セットの標準スキーマサンプル

## Guidelines & Best Practices

- テスト実行時は必ず決定論的サンドボックス環境（`LocalWorkspaceEnv`）を使用し、実環境への不要な副作用を防ぐこと。
- テスト結果は常に構造化 JSON ログとして記録し、`skill-diagnoser` が即座に読み込んで自己修復計画を策定できるようにすること。
- ドキュメント参照だけで十分な仕様確認には無理にスクリプトを多層化せず、`references/` を参照すること。
