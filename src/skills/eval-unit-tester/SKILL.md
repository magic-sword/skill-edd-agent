---
name: eval-unit-tester
description: 指定されたスキルの仕様書（SKILL.md）に基づき、ADK 2.0 に準拠した単体テストケース評価セット（.evalset.json）を自動生成するスキル。
---

## eval-unit-tester スキルの概要

このスキルは、対象スキルのディレクトリにある `SKILL.md` の仕様書や機能記述を読み込み、Gemini API を利用して、ADK 2.0 に完全互換のテストケースデータセット JSON ファイルを自動で作成・保存します。

### 使用方法

スクリプト `scripts/eval_unit_tester.py` を呼び出して、テストケースを生成します。

```bash
python src/skills/eval-unit-tester/scripts/eval_unit_tester.py --skill_name [スキル名]
```

### 入力パラメータ

- `--skill_name <スキル名>` (必須): テストケースを生成したいスキルの名前。

### 出力

- 指定したスキルの `tests/` ディレクトリ内に以下のファイルが生成されます：
  1. `[スキル名]_eval_set.evalset.json` (テストケースファイル)
  2. `test_config.json` (評価設定ファイル)
