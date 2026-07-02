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

## AIエージェント向け使用方法 (FunctionTool)

このスキルをエージェントにバインドして実行する際は、インプロセスの `generate_unit_tests` 関数ツールを直接呼び出してください。

### 共有セッション状態 (Session State) のインターフェース
* **入力値の読み込み**:
  * `skill_name`: 単体テストを生成するスキルの名前
* **出力値の書き込み**:
  * `eval_set_path`: 生成された単体テスト評価アセットのJSONファイルパスを格納します。

### 呼び出し時のパラメータ
* なし (パラメータはセッション状態から自動取得されます)
