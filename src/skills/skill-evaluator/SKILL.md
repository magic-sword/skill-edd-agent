---
name: skill-evaluator
description: This skill should be used when evaluating skills, generating test datasets (evalset.json), running multi-layer test suites, or gating skill tier promotions (Tier 1-3) based on Evaluation-Driven Development.
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Evaluator

## Overview

対象スキルの多層評価テストセット（Trigger, Contract, Golden, Judge, Trajectory, Adversarial）の設計・生成、サンドボックス環境でのシミュレーション実行、および Tier 1（Production）、Tier 2（Verified）、Tier 3（Mastered）への昇格判定を実行する評価エンジン。

## Workflow Decision Tree

評価目的に応じて、以下の決定ロジックに従って評価パイプラインを実行する：

- **If** テストケース（evalset.json）を設計・作成する場合 ➔ **Then** `references/test_types_guide.md` の仕様に従ってエージェントがテストケースを作成するか、`edd-eval generate` コマンドを呼び出す
- **If** 評価セットを実行してスコアを計測する場合 ➔ **Then** `scripts/run_eval.py` を呼び出し、結果を `tests/results/latest_report.json` に構造化ログとして永続化する
- **If** 対象スキルを特定 Tier に昇格・オンボーディング判定する場合 ➔ **Then** `scripts/run_tier_gate.py` を呼び出し、Tier 1〜3 の防壁テストを実行して合格時に `SkillsState` へ登録する

## Step-by-Step Instructions

### Step 1: テストセットの設計・準備
1. `references/test_types_guide.md` を参照し、テストタイプ（`trigger`, `contract`, `golden`, `judge`, `trajectory`, `adversarial`）を選定する。
2. スキルの入出力仕様（`SKILL.md` / `scripts/`）に沿ったテストケースを作成し、`tests/<skill_name>_<type>.evalset.json` に保存する（または `edd-eval generate <skill_name>` を実行）。

### Step 2: 評価シミュレーションの実行 *(Tool: `scripts/run_eval.py`)*
隔離環境（`LocalWorkspaceEnv`）上でテストを実行し、精度（Accuracy）、成功数、失敗ログを収集して `tests/results/latest_report.json` に記録する：
```bash
python scripts/run_eval.py <skill_name> --type all
```

### Step 3: Tier 昇格ゲートキーパー判定 *(Tool: `scripts/run_tier_gate.py`)*
Tier 階層に応じた防壁テストを実行する：
- **Tier 1 (Production)**: 依存関係グラフ検証 (DAG) + 契約テスト (100%合格) + トリガーテスト (精度 90%以上)
- **Tier 2 (Verified)**: Tier 1 要件 + ゴールデンテスト (精度 90%以上) + LLMルーブリックジャッジテスト (精度 85%以上)
- **Tier 3 (Mastered)**: Tier 2 要件 + 推論軌跡テスト (ToolUse一致) + 敵対的堅牢性テスト (精度 90%以上)

実行コマンド:
```bash
python scripts/run_tier_gate.py <skill_name> --tier 1
```

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルの契約テストとトリガーテストを生成・実行してください。"
- "新しいスキル text-analyzer の Tier 1 オンボーディングテストを実行して昇格させて。"
- "data-visualizer スキルのゴールデンテストを実行してスコアレポートを出力してください。"

## When NOT to Use This Skill

- **テスト失敗原因の深掘りや改善計画の策定**: テスト評価ではなく、`skill-diagnoser` を使用する。
- **コードや仕様書の自動パッチ適用・自律修復ループ**: 評価実行ではなく、`skill-optimizer` を使用する。
- **単発の単純な pytest コマンド実行**: 評価データセット（evalset.json）を用いない単純な単体テストは標準ターミナルコマンドで実行する。
- **新規スキルの設計・コード生成**: 評価ゲートではなく、`skill-creator` を使用する。

## Bundled Resources

### `scripts/` (Executable Tools)
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
