---
name: trigger-evaluator
description: 他のスキルのトリガー定義の品質を静的チェック（具体性、明確性）し、トリガー精度検証用の陽性・陰性プロンプト（20件）のテストアセット（.evalset.json）を自動生成するスキル。
---

# トリガー評価・生成スキル

## 概要
このスキルは、指定されたスキルのトリガー定義の品質チェックと、トリガー判定テストケースの自動生成に特化しています。

1. **第1ゲート (静的評価)**: スキルの `SKILL.md` を読み込み、トリガー条件の「具体性（Specificity）」と「明確性（Clarity）」を5点満点で評価します。両方とも4点以上でなければ不合格とし、アセット生成を行わずに処理を終了します。
2. **第2ゲート (テストアセット生成)**: 静的評価に合格した場合、対象スキルがトリガーされるべき陽性プロンプト10件、およびトリガーされるべきではない陰性プロンプト10件の合計20件のテストケースを自動生成し、ADK 2.0 互換の `.evalset.json` および設定ファイルとして対象スキルの `tests/` 配下に保存します。

※ 実際のテストの実行は共通スキル `test-executor` によって行われ、合格・不合格のワークフローは上位エージェントが制御します。

## 使用手順

```bash
python src/skills/trigger-evaluator/scripts/evaluate_trigger.py --skill_name [評価対象のスキル名]
```

### 入力パラメータ

- `--skill_name <スキル名>` (必須): 評価およびテストケースを生成したいスキルの名前。

### 出力

- 静的チェックに合格した場合、指定したスキルの `tests/` ディレクトリ内に以下のファイルが生成されます：
  1. `[スキル名]_trigger_eval.evalset.json` (陽性・陰性テストケース)
  2. `[スキル名]_trigger_eval.evalset.config.json` (評価設定ファイル)
  3. `trigger_eval_report.json` (静的評価と生成結果の詳細レポート)

## AIエージェント向け使用方法 (run_skill_script)

このスキルを実行する際は、`run_skill_script` ツールを使用して、必ず以下の引数構造（JSON）で実行してください。入力・出力はJSONファイルを介してパスでやり取りします。

```json
{
  "skill_name": "trigger-evaluator",
  "file_path": "scripts/evaluate_trigger.py",
  "args": {
    "--input_json": "/workspace/src/.workflow_tmp/<スキル名>/<入力ファイル名>.json",
    "--output_json": "/workspace/src/.workflow_tmp/<スキル名>/<出力ファイル名>.json"
  }
}
```
